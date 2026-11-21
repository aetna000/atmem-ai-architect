import math
from measurement import convert
checks=0
def equal(value,source,target,expected):
 global checks
 assert math.isclose(convert(value,source,target),expected,rel_tol=1e-10,abs_tol=1e-10)
 checks+=1
for args in [(1,"m","cm",100),(1250,"mm","m",1.25),(2.5,"cm","mm",25),(-2,"m","cm",-200),(0,"C","F",32),(212,"F","C",100),(-40,"F","C",-40),(5,"mm","mm",5)]:equal(*args)
for args in [(True,"m","cm"),("2","m","cm"),(float("nan"),"m","cm"),(float("inf"),"C","F"),(1,"m","C"),(1,"M","m"),(1,"m","feet")]:
 try:convert(*args)
 except ValueError:checks+=1
 else:raise AssertionError("Invalid input accepted")
print("INDEPENDENT_ORACLE_PASSED",checks)
