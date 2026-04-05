package main

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/sarchlab/akita/v4/sim"
	"github.com/sarchlab/zeonica/core"
	"github.com/sarchlab/zeonica/runtimecfg"
)

// Conv runs the convolution (element-wise dot product) testbench.
//
// The kernel computes:
//
//	out = 0
//	for x = 0; x < NI*NJ; x++ {
//	    i = x / NJ
//	    j = x % NJ
//	    out += A[i][j] * B[i][j]
//	}
//
// Constants from the compiled YAML: NJ=70, total=4200, so NI=60.
// GEP with 3 operands computes: base + index*4 + offset.
// arg7 = base address of A, arg6 = base address of B.
//
//nolint:gocyclo,funlen
func Conv(rt *runtimecfg.Runtime) int {
	width := rt.Config.Columns
	height := rt.Config.Rows
	driver := rt.Driver
	device := rt.Device
	engine := rt.Engine

	programPath := os.Getenv("ZEONICA_PROGRAM_YAML")
	if programPath == "" {
		programPath = "test/testbench/conv/conv.yaml"
	}
	program := core.LoadProgramFileFromYAML(programPath)
	fmt.Println("program:", program)

	if len(program) == 0 {
		panic("Failed to load program")
	}

	const (
		NI    = 60
		NJ    = 70
		Total = NI * NJ // 4200

		// Base addresses in tile (3,0) memory.
		// GEP computes: base + i*4 + j
		// Max address for one array: (NI-1)*4 + (NJ-1) = 59*4 + 69 = 305
		BaseA = 0
		BaseB = 306
	)

	// Replace arg7 -> #BaseA, arg6 -> #BaseB in the loaded program.
	argReplacements := map[string]string{
		"arg7": fmt.Sprintf("#%d", BaseA),
		"arg6": fmt.Sprintf("#%d", BaseB),
	}
	for coord, prog := range program {
		replaceArgs(&prog, argReplacements)
		program[coord] = prog
	}

	for x := 0; x < width; x++ {
		for y := 0; y < height; y++ {
			coord := fmt.Sprintf("(%d,%d)", x, y)
			if prog, exists := program[coord]; exists {
				driver.MapProgram(prog, [2]int{x, y})
			}
		}
	}

	// Prepare memory for tile (3,0) where LOADs execute.
	// Address space: 0..305 for A, 306..611 for B.
	memSize := BaseB + 306 // 612
	memA := make([]uint32, memSize)
	memB := make([]uint32, memSize)

	// Initialize arrays with simple deterministic data.
	// A[i][j] at address BaseA + i*4 + j
	// B[i][j] at address BaseB + i*4 + j
	// Note: many addresses overlap due to stride 4 < NJ.
	// We write sequentially by (i,j); later writes overwrite earlier ones.
	for i := 0; i < NI; i++ {
		for j := 0; j < NJ; j++ {
			addrA := BaseA + i*4 + j
			addrB := BaseB + i*4 + j
			if addrA < memSize {
				memA[addrA] = uint32((i*(j+1))%NJ + 1)
			}
			if addrB < memSize {
				memB[addrB] = uint32((i*(j+2))%NJ + 1)
			}
		}
	}

	// Merge into a single memory image and preload into tile (3,0).
	mem := make([]uint32, memSize)
	for addr := 0; addr < memSize; addr++ {
		if addr < BaseB {
			mem[addr] = memA[addr]
		} else {
			mem[addr] = memB[addr]
		}
	}
	for addr, val := range mem {
		driver.PreloadMemory(3, 0, val, uint32(addr))
	}

	// Fire all cores.
	for x := 0; x < width; x++ {
		for y := 0; y < height; y++ {
			tile := device.GetTile(x, y)
			tickingComponent := tile.GetTickingComponent()
			engine.Schedule(sim.MakeTickEvent(tickingComponent, 0))
		}
	}

	driver.Run()

	fmt.Println("========================")

	// Read the return value. RETURN_VALUE executes at core (2,0).
	retBits := device.GetTile(2, 0).GetRetVal()
	retVal := int32(retBits)
	fmt.Printf("retVal(bits=0x%08x) -> %d\n", retBits, retVal)

	// Compute expected result matching hardware GEP addressing.
	var expected int32
	for x := 0; x < Total; x++ {
		i := x / NJ
		j := x % NJ
		addrA := BaseA + i*4 + j
		addrB := BaseB + i*4 + j
		valA := int32(mem[addrA])
		valB := int32(mem[addrB])
		expected += valA * valB
	}
	fmt.Printf("expected -> %d\n", expected)

	mismatch := 0
	if retVal == expected {
		fmt.Println("✅ Conv output matches expected")
	} else {
		fmt.Printf("❌ Conv output mismatch: got %d, expected %d\n", retVal, expected)
		mismatch = 1
	}
	return mismatch
}

// replaceArgs replaces arg operand names in all operations of a program.
func replaceArgs(prog *core.Program, replacements map[string]string) {
	for i := range prog.EntryBlocks {
		eb := &prog.EntryBlocks[i]
		for j := range eb.InstructionGroups {
			ig := &eb.InstructionGroups[j]
			for k := range ig.Operations {
				op := &ig.Operations[k]
				for l := range op.SrcOperands.Operands {
					if repl, ok := replacements[op.SrcOperands.Operands[l].Impl]; ok {
						op.SrcOperands.Operands[l].Impl = repl
					}
				}
				for l := range op.DstOperands.Operands {
					if repl, ok := replacements[op.DstOperands.Operands[l].Impl]; ok {
						op.DstOperands.Operands[l].Impl = repl
					}
				}
			}
		}
	}
}

func resolveArchSpecPath() (string, error) {
	fromEnv := strings.TrimSpace(os.Getenv("ZEONICA_ARCH_SPEC"))
	if fromEnv != "" {
		if _, err := os.Stat(fromEnv); err == nil {
			return fromEnv, nil
		}
		return "", fmt.Errorf("ZEONICA_ARCH_SPEC points to a missing file: %s", fromEnv)
	}

	candidates := []string{
		"test/arch_spec/arch_spec.yaml",
		"../../arch_spec/arch_spec.yaml",
	}

	if _, thisFile, _, ok := runtime.Caller(0); ok {
		candidates = append(candidates,
			filepath.Clean(filepath.Join(filepath.Dir(thisFile), "..", "..", "arch_spec", "arch_spec.yaml")),
		)
	}

	seen := make(map[string]struct{}, len(candidates))
	normalized := make([]string, 0, len(candidates))
	for _, candidate := range candidates {
		clean := filepath.Clean(candidate)
		if _, exists := seen[clean]; exists {
			continue
		}
		seen[clean] = struct{}{}
		normalized = append(normalized, clean)
		if _, err := os.Stat(clean); err == nil {
			return clean, nil
		}
	}

	return "", fmt.Errorf("cannot locate arch spec, tried: %s", strings.Join(normalized, ", "))
}

func main() {
	const testName = "conv"

	archSpecPath, err := resolveArchSpecPath()
	if err != nil {
		panic(err)
	}

	rt, err := runtimecfg.LoadRuntime(archSpecPath, testName)
	if err != nil {
		panic(err)
	}

	traceLog, err := rt.InitTraceLogger(core.LevelTrace)
	if err != nil {
		panic(err)
	}

	mismatch := Conv(rt)

	if err := runtimecfg.CloseTraceLog(traceLog); err != nil {
		panic(err)
	}

	passed := mismatch == 0
	reportPath, err := rt.GenerateSaveAndPrintReport(5, &passed, &mismatch)
	if err != nil {
		panic(err)
	}
	fmt.Printf("report saved: %s\n", reportPath)
}
