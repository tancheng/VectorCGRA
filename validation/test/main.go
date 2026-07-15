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

// Spmv runs the SpMV testbench on the configured runtime.
//
// The CGRA compiler maps all array arguments (val, col, row, feature, output)
// to a unified per-tile scratchpad memory starting at address 0.
// All tiles are loaded with the same data via broadcast.
//
// Kernel semantics (per element i):
//
//	temp     = memory[i] * memory[ memory[i] ]
//	memory[ memory[i] ] += temp
//
//nolint:gocyclo,funlen
func Spmv(rt *runtimecfg.Runtime) int {
	width := rt.Config.Columns
	height := rt.Config.Rows
	driver := rt.Driver
	device := rt.Device
	engine := rt.Engine

	programPath := os.Getenv("ZEONICA_PROGRAM_YAML")
	if programPath == "" {
		programPath = "test/testbench/spmv/spmv.yaml"
	}
	program := core.LoadProgramFileFromYAML(programPath)
	fmt.Println("program:", program)

	if len(program) == 0 {
		panic("Failed to load program")
	}

	for x := 0; x < width; x++ {
		for y := 0; y < height; y++ {
			coord := fmt.Sprintf("(%d,%d)", x, y)
			if prog, exists := program[coord]; exists {
				driver.MapProgram(prog, [2]int{x, y})
			}
		}
	}

	// Unified memory model: all arrays share the same address space.
	// memory[i] serves as val[i], col[i], row[i], feature[i], and output[i].
	const nnz = 8

	data := make([]uint32, nnz)
	for i := 0; i < nnz; i++ {
		data[i] = uint32(i)
	}

	// Broadcast data to ALL tiles so every LOAD sees the same initial state.
	for x := 0; x < width; x++ {
		for y := 0; y < height; y++ {
			for addr, val := range data {
				driver.PreloadMemory(x, y, val, uint32(addr))
			}
		}
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

	// Expected output under unified model:
	//   output[i] = initial[row[i]] + val[i] * feature[col[i]]
	//             = memory[i]       + memory[i] * memory[memory[i]]
	//             = i + i * i  =  i * (1 + i)
	expected := computeSpmvUnified(data)

	// STORE tiles determined from the compiled yaml.
	storeTiles := [][2]int{{2, 0}, {3, 0}, {0, 2}, {0, 3}}

	// Collect output: for each address, scan all STORE tiles and pick the
	// value that differs from the initial broadcast (or keep initial if no
	// tile changed it).
	output := make([]uint32, nnz)
	copy(output, data)

	for _, tile := range storeTiles {
		for addr := 0; addr < nnz; addr++ {
			val := driver.ReadMemory(tile[0], tile[1], uint32(addr))
			if val != data[addr] {
				output[addr] = val
			}
		}
	}

	fmt.Println("output (merged from STORE tiles):")
	for i, val := range output {
		fmt.Printf("  addr %d -> %d\n", i, val)
	}

	fmt.Println("expected:")
	mismatch := 0
	for i, val := range expected {
		fmt.Printf("  addr %d -> %d\n", i, val)
		if i < len(output) && output[i] != val {
			mismatch++
		}
	}
	if mismatch == 0 {
		fmt.Println("✅ SpMV output matches expected")
	} else {
		fmt.Printf("❌ SpMV output mismatches: %d\n", mismatch)
	}
	return mismatch
}

// computeSpmvUnified computes expected output under the unified memory model.
// All arrays alias the same memory: val=col=row=feature=output = data[0..n-1].
//
//	output[row[i]] += val[i] * feature[col[i]]
//
// becomes output[data[i]] += data[i] * data[data[i]].
// With data[i] = i this simplifies to output[i] = i + i*i.
func computeSpmvUnified(data []uint32) []uint32 {
	n := len(data)
	result := make([]uint32, n)
	copy(result, data) // initial output = data (aliased)

	for i := 0; i < n; i++ {
		val := data[i]
		colIdx := data[i]
		if int(colIdx) >= n {
			continue
		}
		featureVal := data[colIdx]
		rowIdx := data[i]
		if int(rowIdx) >= n {
			continue
		}
		result[rowIdx] += val * featureVal
	}
	return result
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
	const testName = "spmv"

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

	mismatch := Spmv(rt)

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
