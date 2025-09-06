out = open('wrapper-in', mode='w')
inf = open('wrapper-out', mode='r')

print('select', file=out)
print('foo', file=out)
print('probatio', file=out)
out.flush()

print(inf.readline())

print('explore', file=out)
print('foo', file=out)
print('1', file=out)
print('11234', file=out)
out.flush()

print(inf.readline())

print('guess', file=out)
print('foo', file=out)
print('1 2 3', file=out)
print('1', file=out)
print('1 2 0 1', file=out)
out.flush()

print(inf.readline())