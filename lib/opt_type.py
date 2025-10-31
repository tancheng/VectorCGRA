#=========================================================================
# opt_type.py
#=========================================================================
# Operation types for all functional units.
#
# Author : Cheng Tan
#   Date : Nov 27, 2019

#-------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------

from pymtl3 import *

# Total number of operations that are supported by FUs.
# Needs to be updated once more operations are added/supported.
NUM_OPTS =128

OpCodeType = mk_bits(clog2(NUM_OPTS))

OPT_START                        = OpCodeType( 0  )
OPT_NAH                          = OpCodeType( 1  )
OPT_PAS                          = OpCodeType( 31 )
OPT_CONST                        = OpCodeType( 80 )
OPT_ADD                          = OpCodeType( 2  )
OPT_ADD_CONST                    = OpCodeType( 25 )
OPT_INC                          = OpCodeType( 3  )
OPT_SUB                          = OpCodeType( 4  )
OPT_SUB_CONST                    = OpCodeType( 36 )
OPT_LLS                          = OpCodeType( 5  )
OPT_LRS                          = OpCodeType( 6  )
OPT_MUL                          = OpCodeType( 7  )
OPT_DIV                          = OpCodeType( 26 )
OPT_DIV_CONST                    = OpCodeType( 65 )
OPT_REM                          = OpCodeType( 44 )
OPT_OR                           = OpCodeType( 8  )
OPT_XOR                          = OpCodeType( 9  )
OPT_AND                          = OpCodeType( 10 )
OPT_BIT_NOT                      = OpCodeType( 43 )
OPT_NOT                          = OpCodeType( 11 )
OPT_LD                           = OpCodeType( 12 )
OPT_STR                          = OpCodeType( 13 )
OPT_EQ                           = OpCodeType( 14 )
OPT_EQ_CONST                     = OpCodeType( 33 )
OPT_NE                           = OpCodeType( 45 )
OPT_NE_CONST                     = OpCodeType( 46 )
OPT_RET                          = OpCodeType( 35 )
OPT_GRT_PRED                     = OpCodeType( 16 )
OPT_GRT_ALWAYS                   = OpCodeType( 34 )
OPT_GRT_ONCE                     = OpCodeType( 47 )
OPT_PHI                          = OpCodeType( 17 )
OPT_PHI_CONST                    = OpCodeType( 32 )
OPT_SEL                          = OpCodeType( 27 )
OPT_LD_CONST                     = OpCodeType( 28 )
OPT_STR_CONST                    = OpCodeType( 58 )
OPT_MUL_ADD                      = OpCodeType( 18 )
OPT_MUL_CONST                    = OpCodeType( 29 )
OPT_MUL_CONST_ADD                = OpCodeType( 30 )
OPT_MUL_SUB                      = OpCodeType( 19 )
OPT_MUL_LLS                      = OpCodeType( 20 )
OPT_MUL_LRS                      = OpCodeType( 21 )
OPT_MUL_ADD_LLS                  = OpCodeType( 22 )
OPT_MUL_SUB_LLS                  = OpCodeType( 23 )
OPT_MUL_SUB_LRS                  = OpCodeType( 24 )

OPT_FADD                         = OpCodeType( 37 )
OPT_FSUB                         = OpCodeType( 38 )
OPT_FADD_CONST                   = OpCodeType( 39 )
OPT_FINC                         = OpCodeType( 40 )
OPT_FMUL                         = OpCodeType( 41 )
OPT_FMUL_CONST                   = OpCodeType( 42 )

OPT_VEC_INC                      = OpCodeType( 50 )
OPT_VEC_ADD                      = OpCodeType( 51 )
OPT_VEC_ADD_CONST                = OpCodeType( 52 )
OPT_VEC_SUB                      = OpCodeType( 53 )
OPT_VEC_SUB_CONST                = OpCodeType( 54 )
OPT_VEC_MUL                      = OpCodeType( 55 )
OPT_VEC_INC_COMBINED             = OpCodeType( 70 )
OPT_VEC_ADD_COMBINED             = OpCodeType( 71 )
OPT_VEC_ADD_CONST_COMBINED       = OpCodeType( 72 )
OPT_VEC_SUB_COMBINED             = OpCodeType( 73 )
OPT_VEC_SUB_CONST_COMBINED       = OpCodeType( 74 )
OPT_VEC_MUL_COMBINED             = OpCodeType( 75 )
OPT_VEC_REDUCE_ADD               = OpCodeType( 56 )
OPT_VEC_REDUCE_MUL               = OpCodeType( 57 )
OPT_VEC_REDUCE_ADD_BASE          = OpCodeType( 68 )
OPT_VEC_REDUCE_MUL_BASE          = OpCodeType( 69 )
OPT_VEC_REDUCE_ADD_GLOBAL        = OpCodeType( 76 )
OPT_VEC_REDUCE_MUL_GLOBAL        = OpCodeType( 77 )
OPT_VEC_REDUCE_ADD_BASE_GLOBAL   = OpCodeType( 78 )
OPT_VEC_REDUCE_MUL_BASE_GLOBAL   = OpCodeType( 79 )

OPT_LT                           = OpCodeType( 60 )
OPT_GTE                          = OpCodeType( 61 )
OPT_GT                           = OpCodeType( 62 )
OPT_LTE                          = OpCodeType( 63 )

OPT_DIV_INCLUSIVE_START          = OpCodeType( 48 )
OPT_DIV_INCLUSIVE_END            = OpCodeType( 49 )
OPT_REM_INCLUSIVE_START          = OpCodeType( 59 )
OPT_REM_INCLUSIVE_END            = OpCodeType( 15 )

OPT_SYMBOL_DICT = {
  OPT_START                      : "(start)",
  OPT_NAH                        : "(NAH)",
  OPT_PAS                        : "(->)",
  OPT_CONST                      : "(const)",
  OPT_ADD                        : "(+)",
  OPT_ADD_CONST                  : "(+')",
  OPT_INC                        : "(++)",
  OPT_SUB                        : "(-)",
  OPT_LLS                        : "(<<)",
  OPT_LRS                        : "(>>)",
  OPT_MUL                        : "(*)",
  OPT_DIV                        : "(/)",
  OPT_REM                        : "(%)",
  OPT_OR                         : "(|)",
  OPT_XOR                        : "(^)",
  OPT_AND                        : "(&)",
  OPT_NOT                        : "(!)",
  OPT_BIT_NOT                    : "(~)",
  OPT_LD                         : "(ld)",
  OPT_STR                        : "(st)",
  OPT_EQ                         : "(==)",
  OPT_EQ_CONST                   : "(==')",
  OPT_NE                         : "(!=)",
  OPT_NE_CONST                   : "(!=')",
  OPT_GRT_PRED                   : "(grant_pred)",
  OPT_GRT_ALWAYS                 : "(grant_always)",
  OPT_GRT_ONCE                   : "(grant_once)",
  OPT_RET                        : "(ret)",
  OPT_PHI                        : "(ph)",
  OPT_PHI_CONST                  : "(ph')",
  OPT_SEL                        : "(sel)",
  OPT_LD_CONST                   : "(ldcst)",
  OPT_STR_CONST                  : "(strcst)",
  OPT_MUL_ADD                    : "(* +)",
  OPT_MUL_CONST                  : "(*')",
  OPT_MUL_CONST_ADD              : "(*' +)",
  OPT_MUL_SUB                    : "(* -)",
  OPT_MUL_LLS                    : "(* <<)",
  OPT_MUL_LRS                    : "(* >>)",
  OPT_MUL_ADD_LLS                : "(* + <<)",
  OPT_MUL_SUB_LLS                : "(* + <<)",
  OPT_MUL_SUB_LRS                : "(* - >>)",

  OPT_FADD                       : "(f+)",
  OPT_FADD_CONST                 : "(f+')",
  OPT_FINC                       : "(f++)",
  OPT_FSUB                       : "(f-)",
  OPT_FMUL                       : "(f*)",
  OPT_FMUL_CONST                 : "(f*')",

  OPT_VEC_INC                    : "(v1++)",
  OPT_VEC_ADD                    : "(v1+)",
  OPT_VEC_ADD_CONST              : "(v1+')",
  OPT_VEC_SUB                    : "(v1-)",
  OPT_VEC_SUB_CONST              : "(v1-')",
  OPT_VEC_MUL                    : "(v1*)",
  OPT_VEC_INC_COMBINED           : "(v1++comb)",
  OPT_VEC_ADD_COMBINED           : "(v1+comb)",
  OPT_VEC_ADD_CONST_COMBINED     : "(v1+'comb)",
  OPT_VEC_SUB_COMBINED           : "(v1-comb)",
  OPT_VEC_SUB_CONST_COMBINED     : "(v1-'comb)",
  OPT_VEC_MUL_COMBINED           : "(v1*comb)",
  OPT_VEC_REDUCE_ADD             : "(vreduce+)",
  OPT_VEC_REDUCE_MUL             : "(vreduce*)",
  OPT_VEC_REDUCE_ADD_BASE        : "(vreduce+base)",
  OPT_VEC_REDUCE_MUL_BASE        : "(vreduce*base)",
  OPT_VEC_REDUCE_ADD_GLOBAL      : "(vreduce+global)",
  OPT_VEC_REDUCE_MUL_GLOBAL      : "(vreduce*global)",
  OPT_VEC_REDUCE_ADD_BASE_GLOBAL : "(vreduce+base_global)",
  OPT_VEC_REDUCE_MUL_BASE_GLOBAL : "(vreduce*base_global)",

  OPT_LT                         : "(?<)",
  OPT_GTE                        : "(?>=)",
  OPT_GT                         : "(?>)",
  OPT_LTE                        : "(?<=)",

  OPT_DIV_INCLUSIVE_START        : "(/st)",
  OPT_REM_INCLUSIVE_START        : "(%st)",
  OPT_DIV_INCLUSIVE_END          : "(/ed)",
  OPT_REM_INCLUSIVE_END          : "(%ed)",

}
