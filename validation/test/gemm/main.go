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

// Gemm runs the GEMM (C = C + A*B) testbench on the configured runtime.
//
// Kernel: C[i][j] += sum_k(A[i][k] * B[k][j]) for i,j,k in [0,4).
//
// Memory layout (from compiled YAML):
//   - Tile (2,0): matrix A at base 0 with row stride 4.
//     A[i][k] at address 0 + i*4 + k.
//   - Tile (0,2): matrix B at base 0 with row stride 4.
//     B[k][j] at address 0 + k*4 + j.
//   - Tile (2,0): matrix C at base 16 with row stride 4.
//     C[i][j] at address 16 + i*4 + j.
//
// Arg bindings (YAML immediates):
//
//	#0  = 0   (A base in tile (2,0), B base in tile (0,2))
//	#1  = 1   (loop increment)
//	#4  = 4   (loop bound NI=NJ=NK)
//	#16 = 16  (C base in tile (2,0), after A)
//
//nolint:gocyclo,funlen
func Gemm(rt *runtimecfg.Runtime) int {
	width := rt.Config.Columns
	height := rt.Config.Rows
	driver := rt.Driver
	device := rt.Device
	engine := rt.Engine

	programPath := os.Getenv("ZEONICA_PROGRAM_YAML")
	if programPath == "" {
		programPath = "test/testbench/gemm/gemm.yaml"
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
		N     = 4  // matrix dimension (NI=NJ=NK)
		BaseA = 0  // A base address in tile (2,0)
		BaseB = 0  // B base address in tile (0,2)
		BaseC = 16 // C base address in tile (2,0), after A
	)

	// Initialize matrices per PolyBench gemm_int.c init_array.
	// A[i][j] = (i * (j+1)) % 17
	// B[i][j] = (i * (j+2)) % 19
	// C[i][j] = (i * j) % 13
	dataA := make([]int32, N*N)
	dataB := make([]int32, N*N)
	dataC := make([]int32, N*N)

	for i := 0; i < N; i++ {
		for j := 0; j < N; j++ {
			dataA[i*N+j] = int32((i * (j + 1)) % 17)
			dataB[i*N+j] = int32((i * (j + 2)) % 19)
			dataC[i*N+j] = int32((i * j) % 13)
		}
	}

	// Preload A into tile (2,0) at addresses BaseA + i*4 + k.
	for i := 0; i < N; i++ {
		for k := 0; k < N; k++ {
			addr := BaseA + i*N + k
			driver.PreloadMemory(2, 0, uint32(dataA[i*N+k]), uint32(addr))
		}
	}

	// Preload C into tile (2,0) at addresses BaseC + i*4 + j.
	for i := 0; i < N; i++ {
		for j := 0; j < N; j++ {
			addr := BaseC + i*N + j
			driver.PreloadMemory(2, 0, uint32(dataC[i*N+j]), uint32(addr))
		}
	}

	// Preload B into tile (0,2) at addresses BaseB + k*4 + j.
	for k := 0; k < N; k++ {
		for j := 0; j < N; j++ {
			addr := BaseB + k*N + j
			driver.PreloadMemory(0, 2, uint32(dataB[k*N+j]), uint32(addr))
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

	// Read output C from tile (2,0) at addresses BaseC..BaseC+15.
	outputC := make([]int32, N*N)
	for i := 0; i < N; i++ {
		for j := 0; j < N; j++ {
			addr := BaseC + i*N + j
			val := driver.ReadMemory(2, 0, uint32(addr))
			outputC[i*N+j] = int32(val)
			fmt.Printf("  C[%d][%d] = %d\n", i, j, outputC[i*N+j])
		}
	}

	// Compute expected: C[i][j] = C_init[i][j] + sum_k(A[i][k] * B[k][j]).
	expectedC := make([]int32, N*N)
	copy(expectedC, dataC)
	for i := 0; i < N; i++ {
		for k := 0; k < N; k++ {
			for j := 0; j < N; j++ {
				expectedC[i*N+j] += dataA[i*N+k] * dataB[k*N+j]
			}
		}
	}

	fmt.Println("expected:")
	mismatch := 0
	for i := 0; i < N; i++ {
		for j := 0; j < N; j++ {
			fmt.Printf("  C[%d][%d] = %d\n", i, j, expectedC[i*N+j])
			if outputC[i*N+j] != expectedC[i*N+j] {
				mismatch++
			}
		}
	}

	if mismatch == 0 {
		fmt.Println("GEMM output matches expected")
	} else {
		fmt.Printf("GEMM output mismatches: %d\n", mismatch)
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
	const testName = "gemm"

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

	mismatch := Gemm(rt)

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
