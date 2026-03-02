#!/bin/bash
# ==========================================================================
# Wrapper script to run Vivado synthesis for ZCU102 BRAM design
# ==========================================================================
# Usage: ./run_synthesis.sh [options]
#
# Options:
#   -d, --dir <path>       RTL directory (default: ./rtl)
#   -t, --top <module>     Top module name (default: auto-detect)
#   -o, --output <path>    Output directory (default: ./vivado_output)
#   -g, --gui              Launch Vivado GUI after synthesis
#   -h, --help             Show this help message
# ==========================================================================

# Default configuration
RTL_DIR="./"
TOP_MODULE="STEP_BRAMRTL__39ff07219eff1cde"
OUTPUT_DIR="./vivado_output"
LAUNCH_GUI=0
TCL_SCRIPT="synthesize_bram.tcl"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dir)
            RTL_DIR="$2"
            shift 2
            ;;
        -t|--top)
            TOP_MODULE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -g|--gui)
            LAUNCH_GUI=1
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -d, --dir <path>       RTL directory (default: ./rtl)"
            echo "  -t, --top <module>     Top module name (default: auto-detect)"
            echo "  -o, --output <path>    Output directory (default: ./vivado_output)"
            echo "  -g, --gui              Launch Vivado GUI after synthesis"
            echo "  -h, --help             Show this help message"
            echo ""
            echo "Example:"
            echo "  $0 -d ./generated_sv -t my_top_module"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Print configuration
echo "=========================================="
echo "Vivado Synthesis Configuration"
echo "=========================================="
echo "RTL Directory:   $RTL_DIR"
echo "Top Module:      $TOP_MODULE"
echo "Output Directory: $OUTPUT_DIR"
echo "=========================================="
echo ""

# Check if Vivado is available
if ! command -v vivado &> /dev/null; then
    echo -e "${RED}ERROR: Vivado not found in PATH${NC}"
    echo "Please source Vivado settings, e.g.:"
    echo "  source /tools/Xilinx/Vivado/2023.2/settings64.sh"
    exit 1
fi

# Check Vivado version
VIVADO_VERSION=$(vivado -version | head -n 1)
echo "Using: $VIVADO_VERSION"
echo ""

# Check if RTL directory exists
if [ ! -d "$RTL_DIR" ]; then
    echo -e "${YELLOW}WARNING: RTL directory not found: $RTL_DIR${NC}"
    echo "Creating directory..."
    mkdir -p "$RTL_DIR"
fi

# Count design files
SV_COUNT=$(find "$RTL_DIR" -name "*.sv" 2>/dev/null | wc -l)
V_COUNT=$(find "$RTL_DIR" -name "*.v" 2>/dev/null | wc -l)
TOTAL_FILES=$((SV_COUNT + V_COUNT))

if [ $TOTAL_FILES -eq 0 ]; then
    echo -e "${RED}ERROR: No .sv or .v files found in $RTL_DIR${NC}"
    echo "Please place your SystemVerilog/Verilog files in $RTL_DIR"
    exit 1
fi

echo "Found $SV_COUNT SystemVerilog files and $V_COUNT Verilog files"
echo ""

# Create temporary TCL script with configuration
TEMP_TCL="${OUTPUT_DIR}/temp_synth_config.tcl"
mkdir -p "$OUTPUT_DIR"

cat > "$TEMP_TCL" << EOF
# Auto-generated configuration
set PART "xczu9eg-ffvb1156-2-e"
set TOP_MODULE "$TOP_MODULE"
set PROJECT_NAME "cgra_bram_synth"
set OUTPUT_DIR "$OUTPUT_DIR"
set RTL_DIR "$RTL_DIR"
set REPORTS_DIR "\${OUTPUT_DIR}/reports"

# Source the main synthesis script
source $TCL_SCRIPT
EOF

# Run Vivado synthesis
echo "Starting Vivado synthesis..."
echo "Log file: ${OUTPUT_DIR}/vivado_synth.log"
echo ""

vivado -mode batch -source "$TEMP_TCL" -log "${OUTPUT_DIR}/vivado_synth.log" -journal "${OUTPUT_DIR}/vivado_synth.jou"

# Check synthesis result
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "Synthesis completed successfully!"
    echo -e "==========================================${NC}"
    echo ""
    echo "Output files are in: $OUTPUT_DIR"
    echo ""
    echo "Key reports:"
    echo "  - ${OUTPUT_DIR}/reports/utilization_summary.rpt"
    echo "  - ${OUTPUT_DIR}/reports/utilization_hierarchical.rpt"
    echo ""
    
    # Quick BRAM check
    if [ -f "${OUTPUT_DIR}/reports/utilization_summary.rpt" ]; then
        echo "BRAM Usage Summary:"
        grep -A 5 "Block RAM" "${OUTPUT_DIR}/reports/utilization_summary.rpt" || echo "  (Check report for details)"
        echo ""
    fi
    
    # Launch GUI if requested
    if [ $LAUNCH_GUI -eq 1 ]; then
        echo "Launching Vivado GUI..."
        vivado "${OUTPUT_DIR}/post_synth.dcp" &
    fi
    
else
    echo ""
    echo -e "${RED}=========================================="
    echo "Synthesis FAILED!"
    echo -e "==========================================${NC}"
    echo ""
    echo "Check log file: ${OUTPUT_DIR}/vivado_synth.log"
    echo ""
    exit 1
fi

# Cleanup temp file
rm -f "$TEMP_TCL"

echo "Done!"