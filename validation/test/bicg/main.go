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

// BiCG runs the BiCG testbench on the configured runtime.
//
// Kernel (from bicg.c.txt):
//
//	for j in [0,M): s[j] = 0
//	for i in [0,N):
//	    q[i] = 0
//	    for j in [0,M):
//	        a = A[i*M + j]
//	        s[j] += r[i] * a
//	        q[i] += a * p[j]
//
// Memory layout (from compiled YAML):
//   - Tile (0,2): matrix A at base 0, row stride 32 (SHL #5).
//     A[i][j] at address 0 + i*32 + j.
//   - Tile (1,0): vector p at base 0 and vector s at base 8.
//     p[j] at address 0 + j, s[j] at address 8 + j.
//   - Tile (0,1): vector r at base 0.
//     r[i] at address 0 + i.
//   - Tile (0,3): vector q at base 0.
//     q[i] at address 0 + i.
//
// Arg bindings (set in YAML as immediates):
//
//	arg0 = #0  (A base in tile (0,2))
//	arg1 = #0  (p base in tile (1,0))
//	arg2 = #0  (r base in tile (0,1))
//	arg3 = #8  (s base in tile (1,0), after p)
//	arg4 = #0  (q base in tile (0,3))
//
//nolint:gocyclo,funlen
func BiCG(rt *runtimecfg.Runtime) int {
	width := rt.Config.Columns
	height := rt.Config.Rows
	driver := rt.Driver
	device := rt.Device
	engine := rt.Engine

	programPath := os.Getenv("ZEONICA_PROGRAM_YAML")
	if programPath == "" {
		programPath = "test/testbench/bicg/bicg.yaml"
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
		M         = 8  // inner dimension
		N         = 8  // outer dimension
		RowStride = 32 // A row stride (SHL #5)
		BaseA     = 0  // arg0: A base in tile (0,2)
		BaseP     = 0  // arg1: p base in tile (1,0)
		BaseR     = 0  // arg2: r base in tile (0,1)
		BaseS     = 8  // arg3: s base in tile (1,0)
		BaseQ     = 0  // arg4: q base in tile (0,3)
	)

	// Initialize input data.
	dataA := make([]int32, N*M)
	dataP := make([]int32, M)
	dataR := make([]int32, N)

	for i := 0; i < N; i++ {
		for j := 0; j < M; j++ {
			dataA[i*M+j] = int32((i*(j+1))%17 + 1)
		}
	}
	for j := 0; j < M; j++ {
		dataP[j] = int32((j*3)%13 + 1)
	}
	for i := 0; i < N; i++ {
		dataR[i] = int32((i*2)%11 + 1)
	}

	// Preload A into tile (0,2) with row stride 32.
	for i := 0; i < N; i++ {
		for j := 0; j < M; j++ {
			addr := BaseA + i*RowStride + j
			driver.PreloadMemory(0, 2, uint32(dataA[i*M+j]), uint32(addr))
		}
	}

	// Preload p into tile (1,0) at addresses 0..7.
	for j := 0; j < M; j++ {
		driver.PreloadMemory(1, 0, uint32(dataP[j]), uint32(BaseP+j))
	}

	// Preload r into tile (0,1) at addresses 0..7.
	for i := 0; i < N; i++ {
		driver.PreloadMemory(0, 1, uint32(dataR[i]), uint32(BaseR+i))
	}

	// Pre-initialize s to 0 in tile (1,0) at addresses 8..15.
	for j := 0; j < M; j++ {
		driver.PreloadMemory(1, 0, 0, uint32(BaseS+j))
	}

	// Pre-initialize q to 0 in tile (0,3) at addresses 0..7.
	for i := 0; i < N; i++ {
		driver.PreloadMemory(0, 3, 0, uint32(BaseQ+i))
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

	// Read output s from tile (1,0) at addresses 8..15.
	outputS := make([]int32, M)
	for j := 0; j < M; j++ {
		val := driver.ReadMemory(1, 0, uint32(BaseS+j))
		outputS[j] = int32(val)
		fmt.Printf("  s[%d] = %d\n", j, outputS[j])
	}

	// Read output q from tile (0,3) at addresses 0..7.
	outputQ := make([]int32, N)
	for i := 0; i < N; i++ {
		val := driver.ReadMemory(0, 3, uint32(BaseQ+i))
		outputQ[i] = int32(val)
		fmt.Printf("  q[%d] = %d\n", i, outputQ[i])
	}

	// Compute expected results.
	expectedS := make([]int32, M)
	expectedQ := make([]int32, N)
	for i := 0; i < N; i++ {
		for j := 0; j < M; j++ {
			a := dataA[i*M+j]
			expectedS[j] += dataR[i] * a
			expectedQ[i] += a * dataP[j]
		}
	}

	fmt.Println("expected s:")
	mismatch := 0
	for j := 0; j < M; j++ {
		fmt.Printf("  s[%d] = %d\n", j, expectedS[j])
		if outputS[j] != expectedS[j] {
			mismatch++
		}
	}

	fmt.Println("expected q:")
	for i := 0; i < N; i++ {
		fmt.Printf("  q[%d] = %d\n", i, expectedQ[i])
		if outputQ[i] != expectedQ[i] {
			mismatch++
		}
	}

	if mismatch == 0 {
		fmt.Println("BiCG output matches expected")
	} else {
		fmt.Printf("BiCG output mismatches: %d\n", mismatch)
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
	const testName = "bicg"

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

	mismatch := BiCG(rt)

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
