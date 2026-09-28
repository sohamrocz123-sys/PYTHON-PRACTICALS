def isPalindrome(n):
  k = str(n)
  return k == k[::-1]

n = int(input())
print(isPalindrome(n))