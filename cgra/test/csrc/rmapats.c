// file = 0; split type = patterns; threshold = 100000; total count = 0.
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include "rmapats.h"

void  hsG_0__0 (struct dummyq_struct * I1381, EBLK  * I1376, U  I616);
void  hsG_0__0 (struct dummyq_struct * I1381, EBLK  * I1376, U  I616)
{
    U  I1644;
    U  I1645;
    U  I1646;
    struct futq * I1647;
    struct dummyq_struct * pQ = I1381;
    I1644 = ((U )vcs_clocks) + I616;
    I1646 = I1644 & ((1 << fHashTableSize) - 1);
    I1376->I662 = (EBLK  *)(-1);
    I1376->I663 = I1644;
    if (0 && rmaProfEvtProp) {
        vcs_simpSetEBlkEvtID(I1376);
    }
    if (I1644 < (U )vcs_clocks) {
        I1645 = ((U  *)&vcs_clocks)[1];
        sched_millenium(pQ, I1376, I1645 + 1, I1644);
    }
    else if ((peblkFutQ1Head != ((void *)0)) && (I616 == 1)) {
        I1376->I665 = (struct eblk *)peblkFutQ1Tail;
        peblkFutQ1Tail->I662 = I1376;
        peblkFutQ1Tail = I1376;
    }
    else if ((I1647 = pQ->I1284[I1646].I685)) {
        I1376->I665 = (struct eblk *)I1647->I683;
        I1647->I683->I662 = (RP )I1376;
        I1647->I683 = (RmaEblk  *)I1376;
    }
    else {
        sched_hsopt(pQ, I1376, I1644);
    }
}
#ifdef __cplusplus
extern "C" {
#endif
void SinitHsimPats(void);
#ifdef __cplusplus
}
#endif
