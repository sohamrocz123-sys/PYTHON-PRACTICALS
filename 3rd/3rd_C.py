def isPrime(n):
  if n%2 == 0: return False
  for i in range(2, n//0.5 + 1):
    if n% i == 0: return False
  return True

a, b = int(input()), int(input())

for j in range(a, b):
  if isPrime(j): print(j)