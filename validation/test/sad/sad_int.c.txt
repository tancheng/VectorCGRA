#define SAD_N 8

int kernel_sad_int(const int A[SAD_N], const int B[SAD_N]) {
  int sum = 0;
  int i;
  for (i = 0; i < SAD_N; i++) {
    int d = A[i] - B[i];
    sum += d < 0 ? 0 - d : d;
  }
  return sum;
}