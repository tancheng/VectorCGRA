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

// Gemv runs the GEMV (y = A*x) testbench on the configured runtime.
//
// Kernel: y[i] = sum_j(A[i][j] * x[j]) for i,j in [0,4).
//
// Memory layout (from compiled YAML):
//   - Tile (1,0): matrix A with row stride 16 (SHL #4).
//     A[i][j] at address arg0 + i*16 + j.
//   - Tile (2,0): vector x at arg1+j, output y at arg2+i.
//
// Arg bindings (set in YAML as immediates):
//
//	arg0 = #0  (A base in tile (1,0))
//	arg1 = #0  (x base in tile (2,0))
//	arg2 = #4  (y base in tile (2,0), after x)
//
//nolint:gocyclo,funlen
func Gemv(rt *runtimecfg.Runtime) int {
	width := rt.Config.Columns
	height := rt.Config.Rows
	driver := rt.Driver
	device := rt.Device
	engine := rt.Engine

	programPath := os.Getenv("ZEONICA_PROGRAM_YAML")
	if programPath == "" {
		programPath = "test/testbench/gemv/gemv-v4.yaml"
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
		N        = 4 // matrix/vector dimension
		RowShift = 2 // SHL amount in YAML
		BaseA    = 0 // arg0: A base in tile (1,0)
		BaseX    = 0 // arg1: x base in tile (2,0)
		BaseY    = 4 // arg2: y base in tile (2,0)
	)

	rowStride := 1 << RowShift // 16

	// A is a 4x4 matrix.
	dataA := []int32{
		1, 2, 3, 4,
		5, 6, 7, 8,
		9, 10, 11, 12,
		13, 14, 15, 16,
	}

	// x is a 4-element vector.
	dataX := []int32{10, 20, 30, 40}

	// Preload A into tile (1,0) with row stride 16.
	for i := 0; i < N; i++ {
		for j := 0; j < N; j++ {
			addr := BaseA + i*rowStride + j
			driver.PreloadMemory(1, 0, uint32(dataA[i*N+j]), uint32(addr))
		}
	}

	// Preload x into tile (2,0) at addresses BaseX..BaseX+3.
	for j := 0; j < N; j++ {
		driver.PreloadMemory(2, 0, uint32(dataX[j]), uint32(BaseX+j))
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

	// Read output y from tile (2,0) at addresses BaseY..BaseY+3.
	outputY := make([]int32, N)
	for i := 0; i < N; i++ {
		val := driver.ReadMemory(2, 0, uint32(BaseY+i))
		outputY[i] = int32(val)
		fmt.Printf("  y[%d] = %d\n", i, outputY[i])
	}

	// Compute expected: y[i] = sum_j(A[i][j] * x[j]).
	expectedY := make([]int32, N)
	for i := 0; i < N; i++ {
		for j := 0; j < N; j++ {
			expectedY[i] += dataA[i*N+j] * dataX[j]
		}
	}

	fmt.Println("expected:")
	mismatch := 0
	for i := 0; i < N; i++ {
		fmt.Printf("  y[%d] = %d\n", i, expectedY[i])
		if outputY[i] != expectedY[i] {
			mismatch++
		}
	}

	if mismatch == 0 {
		fmt.Println("✅ GEMV output matches expected")
	} else {
		fmt.Printf("❌ GEMV output mismatches: %d\n", mismatch)
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
	const testName = "gemv"

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

	mismatch := Gemv(rt)

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
