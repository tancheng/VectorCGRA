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

// SAD runs the SAD (Sum of Absolute Differences) testbench.
//
// Kernel:
//
//	sum = 0
//	for i in [0, SAD_N):
//	    d = A[i] - B[i]
//	    sum += d < 0 ? -d : d
//	return sum
//
// Memory layout (from compiled YAML):
//   - Tile (2,0): array A at base 0. A[i] at address 0 + i.
//   - Tile (3,0): array B at base 0. B[i] at address 0 + i.
//
// Return value read from tile (1,1) via GetRetVal().
//
// Arg bindings:
//
//	arg0 = #0  (A base in tile (2,0))
//	arg1 = #0  (B base in tile (3,0))
//
//nolint:gocyclo,funlen
func SAD(rt *runtimecfg.Runtime) int {
	width := rt.Config.Columns
	height := rt.Config.Rows
	driver := rt.Driver
	device := rt.Device
	engine := rt.Engine

	programPath := os.Getenv("ZEONICA_PROGRAM_YAML")
	if programPath == "" {
		programPath = "test/testbench/sad/sad.yaml"
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

	const (
		N     = 8 // SAD_N
		BaseA = 0 // arg0: A base in tile (2,0)
		BaseB = 0 // arg1: B base in tile (3,0)
	)

	// Initialize input data.
	dataA := []int32{3, -7, 12, 0, 5, -1, 8, -4}
	dataB := []int32{1, 2, -3, 4, -5, 6, 7, 8}

	// Preload A into tile (2,0).
	for i := 0; i < N; i++ {
		driver.PreloadMemory(2, 0, uint32(dataA[i]), uint32(BaseA+i))
	}

	// Preload B into tile (3,0).
	for i := 0; i < N; i++ {
		driver.PreloadMemory(3, 0, uint32(dataB[i]), uint32(BaseB+i))
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

	// Read return value from tile (1,1).
	retBits := device.GetTile(1, 1).GetRetVal()
	retVal := int32(retBits)
	fmt.Printf("retVal(bits=0x%08x) -> %d\n", retBits, retVal)

	// Compute expected SAD.
	var expected int32
	for i := 0; i < N; i++ {
		d := dataA[i] - dataB[i]
		if d < 0 {
			d = -d
		}
		expected += d
	}
	fmt.Printf("expected -> %d\n", expected)

	mismatch := 0
	if retVal == expected {
		fmt.Println("SAD output matches expected")
	} else {
		fmt.Printf("SAD output mismatch: got %d, expected %d\n", retVal, expected)
		mismatch = 1
	}
	return mismatch
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
	const testName = "sad"

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

	mismatch := SAD(rt)

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
