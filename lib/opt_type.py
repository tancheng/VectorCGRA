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
NUM_OPTS = 64

OPT_START                 = Bits6( 0  )
OPT_NAH                   = Bits6( 1  )
OPT_PAS                   = Bits6( 31 )
OPT_ADD                   = Bits6( 2  )
OPT_ADD_CONST             = Bits6( 25 )
OPT_INC                   = Bits6( 3  )
OPT_SUB                   = Bits6( 4  )
OPT_SUB_CONST             = Bits6( 36 )
OPT_LLS                   = Bits6( 5  )
OPT_LRS                   = Bits6( 6  )
OPT_MUL                   = Bits6( 7  )
OPT_DIV                   = Bits6( 26 )
OPT_DIV_CONST             = Bits6( 26 )
OPT_REM                   = Bits6( 44 )
OPT_OR                    = Bits6( 8  )
OPT_XOR                   = Bits6( 9  )
OPT_AND                   = Bits6( 10 )
OPT_BIT_NOT               = Bits6( 43 )
OPT_NOT                   = Bits6( 11 )
OPT_LD                    = Bits6( 12 )
OPT_STR                   = Bits6( 13 )
OPT_EQ                    = Bits6( 14 )
OPT_EQ_CONST              = Bits6( 33 )
OPT_NE                    = Bits6( 45 )
OPT_NE_CONST              = Bits6( 46 )
OPT_RET                   = Bits6( 35 )
OPT_GRT_PRED              = Bits6( 16 )
OPT_GRT_ALWAYS            = Bits6( 34 )
OPT_GRT_ONCE              = Bits6( 47 )
OPT_PHI                   = Bits6( 17 )
OPT_PHI_CONST             = Bits6( 32 )
OPT_SEL                   = Bits6( 27 )
OPT_LD_CONST              = Bits6( 28 )
OPT_STR_CONST             = Bits6( 58 )
OPT_MUL_ADD               = Bits6( 18 )
OPT_MUL_CONST             = Bits6( 29 )
OPT_MUL_CONST_ADD         = Bits6( 30 )
OPT_MUL_SUB               = Bits6( 19 )
OPT_MUL_LLS               = Bits6( 20 )
OPT_MUL_LRS               = Bits6( 21 )
OPT_MUL_ADD_LLS           = Bits6( 22 )
OPT_MUL_SUB_LLS           = Bits6( 23 )
OPT_MUL_SUB_LRS           = Bits6( 24 )

OPT_FADD                  = Bits6( 37 )
OPT_FSUB                  = Bits6( 38 )
OPT_FADD_CONST            = Bits6( 39 )
OPT_FINC                  = Bits6( 40 )
OPT_FMUL                  = Bits6( 41 )
OPT_FMUL_CONST            = Bits6( 42 )

OPT_VEC_ADD          = Bits6( 50 )
OPT_VEC_INC          = Bits6( 51 )
OPT_VEC_ADD_CONST    = Bits6( 52 )
OPT_VEC_SUB          = Bits6( 53 )
OPT_VEC_SUB_CONST    = Bits6( 54 )
OPT_VEC_MUL          = Bits6( 55 )
OPT_VEC_REDUCE_ADD   = Bits6( 56 )
OPT_VEC_REDUCE_MUL   = Bits6( 57 )

OPT_LT  = Bits6( 60 )
OPT_GTE = Bits6( 61 )
OPT_GT  = Bits6( 62 )
OPT_LTE = Bits6( 63 )

OPT_DIV_INCLUSIVE_START = Bits6( 48 )
OPT_DIV_INCLUSIVE_END   = Bits6( 49 )
OPT_REM_INCLUSIVE_START = Bits6( 59 )
OPT_REM_INCLUSIVE_END   = Bits6( 15 )

OPT_SYMBOL_DICT = {
  OPT_START         : "(start)",
  OPT_NAH           : "(NAH)",
  OPT_PAS           : "(->)",
  OPT_ADD           : "(+)",
  OPT_ADD_CONST     : "(+')",
  OPT_INC           : "(++)",
  OPT_SUB           : "(-)",
  OPT_LLS           : "(<<)",
  OPT_LRS           : "(>>)",
  OPT_MUL           : "(*)",
  OPT_DIV           : "(/)",
  OPT_REM           : "(%)",
  OPT_OR            : "(|)",
  OPT_XOR           : "(^)",
  OPT_AND           : "(&)",
  OPT_NOT           : "(!)",
  OPT_BIT_NOT       : "(~)",
  OPT_LD            : "(ld)",
  OPT_STR           : "(st)",
  OPT_EQ            : "(==)",
  OPT_EQ_CONST      : "(==')",
  OPT_NE            : "(!=)",
  OPT_NE_CONST      : "(!=')",
  OPT_GRT_PRED      : "(grant_pred)",
  OPT_GRT_ALWAYS    : "(grant_always)",
  OPT_GRT_ONCE      : "(grant_once)",
  OPT_RET           : "(ret)",
  OPT_PHI           : "(ph)",
  OPT_PHI_CONST     : "(ph')",
  OPT_SEL           : "(sel)",
  OPT_LD_CONST      : "(ldcst)",
  OPT_STR_CONST     : "(strcst)",
  OPT_MUL_ADD       : "(* +)",
  OPT_MUL_CONST     : "(*')",
  OPT_MUL_CONST_ADD : "(*' +)",
  OPT_MUL_SUB       : "(* -)",
  OPT_MUL_LLS       : "(* <<)",
  OPT_MUL_LRS       : "(* >>)",
  OPT_MUL_ADD_LLS   : "(* + <<)",
  OPT_MUL_SUB_LLS   : "(* + <<)",
  OPT_MUL_SUB_LRS   : "(* - >>)",

  OPT_FADD           : "(f+)",
  OPT_FADD_CONST     : "(f+')",
  OPT_FINC           : "(f++)",
  OPT_FSUB           : "(f-)",
  OPT_FMUL           : "(f*)",
  OPT_FMUL_CONST     : "(f*')",

  OPT_VEC_ADD         : "(v1+)",
  OPT_VEC_INC         : "(v1++)",
  OPT_VEC_ADD_CONST   : "(v1+')",
  OPT_VEC_SUB         : "(v1-)",
  OPT_VEC_SUB_CONST   : "(v1-')",
  OPT_VEC_MUL         : "(v1*)",
  OPT_VEC_REDUCE_ADD  : "(vall+)",
  OPT_VEC_REDUCE_MUL  : "(vall*)",

  OPT_LT  : "(?<)",
  OPT_GTE : "(?>=)",
  OPT_GT  : "(?>)",
  OPT_LTE : "(?<=)",

  OPT_DIV_INCLUSIVE_START   : "(/st)",
  OPT_REM_INCLUSIVE_START   : "(%st)",
  OPT_DIV_INCLUSIVE_END     : "(/ed)",
  OPT_REM_INCLUSIVE_END     : "(%ed)",

}
