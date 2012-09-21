import pulp
from pulp.solvers import GLPK


prob = pulp.LpProblem("test",pulp.LpMinimize)

c1 = 0.3
m1 = 0.1
n1 = 0.5
c2 = 0.7
m2 = 0.1
n2 = 0.3

x11 = pulp.LpVariable("x11",0,1,'Integer')
x12 = pulp.LpVariable("x11",0,1,'Integer')
x12 = pulp.LpVariable("x12",0,1,'Integer')
x21 = pulp.LpVariable("x21",0,1,'Integer')
x22 = pulp.LpVariable("x22",0,1,'Integer')

u1 = pulp.LpVariable("u1",0,1,'Integer')
u2 = pulp.LpVariable("u2",0,1,'Integer')

prob += x11 + x12 == 1
prob += x21 + x22 == 1

#prob += u1 + u2 - x11 - x12 == 0
#prob += u1 + u2 - x21 - x22 == 0

prob += u1 >= x11
prob += u1 >= x21

prob += u2 >= x12
prob += u2 >= x22

prob += n1 * x11 + n2 * x21 <= 1
prob += m1 * x11 + m2 * x21 <= 1
prob += c1 * x11 + c2 * x21 <= 1
prob += n1 * x12 + n2 * x22 <= 1
prob += m1 * x12 + m2 * x22 <= 1
prob += c1 * x12 + c2 * x22 <= 1




prob += u1 + u2


GLPK().solve(prob)

for v in prob.variables():
	print v.name, "=", v.varValue

print "objective=", value(prob.objective)



