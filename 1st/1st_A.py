num1=float(input("Enter the first no."))
num2=float(input("Enter the first no."))
add=num1+num2
sub=num1-num2
mul=num1*num2
if num2!=0:
    division=num1/num2
else:
    division="Undefined"
print(f"\nResults")
print(f"Addition:{num1}+{num2}={add}")
print(f"Subtraction:{num1}-{num2}={sub}")
print(f"Multiplication:{num1}*{num2}={mul}")
print(f"Division:{num1}/{num2}={division}")