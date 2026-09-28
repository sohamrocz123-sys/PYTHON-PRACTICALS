def simpleint(p, r, t):
  return p * r * t * 0.01

p = int(input("principle: "))
r = int(input("rate: "))
t = int(input("time(years): "))

print(simpleint(p, r, t))
