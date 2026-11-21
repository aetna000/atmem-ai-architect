
import random
from rainfall import total_mm
checks=0
def equal(values,expected):
 global checks
 before=list(values);assert total_mm(values)==expected,(values,expected);assert values==before;checks+=1
equal([],0);equal([9],9);equal([3,7,11],21);equal([0]*366,0);equal([1]*366,366);equal([10**400,0],10**400)
rng=random.Random(7159)
for size in range(1,80):
 values=[rng.randrange(10000)/8 for _ in range(size)];equal(values,sum(values))
for value in [True,False,None,'1','',{},[],1j,-1,-.1,float('inf'),float('-inf'),float('nan')]:
 try:total_mm([1,2,value])
 except TypeError:checks+=1
 else:raise AssertionError(('invalid reading accepted',repr(value)))
for value in [None,{},(),(1,2),'1',True,1,1.0,range(3)]:
 try:total_mm(value)
 except TypeError:checks+=1
 else:raise AssertionError(('non-list accepted',repr(value)))
try:total_mm([0]*367)
except ValueError:checks+=1
else:raise AssertionError('limit ignored')
print('INDEPENDENT_RAINFALL_PASSED',checks)
