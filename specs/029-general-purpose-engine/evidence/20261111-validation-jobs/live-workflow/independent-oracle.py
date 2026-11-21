from line_summary import summarize
checks=0
def expect(lines,count,total,nonempty):
 global checks
 before=list(lines)
 assert summarize(lines)=={'count':count,'total_characters':total,'nonempty_count':nonempty}
 assert lines==before
 checks+=1
expect([],0,0,0)
expect(['','  ','a','é'],4,4,2)
expect(['x'*4096],1,4096,1)
expect(['a']*1000,1000,1000,1000)
for invalid in [None,'abc',('a',),[1],[True],[None]]:
 try:summarize(invalid)
 except TypeError:checks+=1
 else:raise AssertionError('Invalid input type accepted')
for invalid in [['x'*4097],['']*1001]:
 try:summarize(invalid)
 except ValueError:checks+=1
 else:raise AssertionError('Oversized input accepted')
original=['one','two'];summarize(original);assert original==['one','two'];checks+=1
expect(['\t','\n',' a '],3,5,1)
expect(['😀'],1,1,1)
print('INDEPENDENT_LINE_SUMMARY_ORACLE_PASSED',checks)
