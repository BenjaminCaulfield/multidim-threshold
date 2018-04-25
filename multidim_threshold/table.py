import math

#assuming all corners contain points
class Table:
    def __init__(self, table_array, dimensions, w):
        self.table = table_array
        self.dims = dimensions
        self.width = w #number of points in any dimension. 
        assert int(w**dimensions) == len(table_array)
    def lookup(self, coords):
        index = 0
        for i in range(0, len(coords)):
            assert coords[i] < self.width
            index += coords[i]*(self.width**i) 
        return self.table[index]
    def check_val(self, coords):
        assert len(coords) == self.dims
        uppercoords = []
        lowercoords = []
        for i in range(0, len(coords)):
            x = coords[i]*(self.width-1)
            uppercoords.append(int(math.ceil(x)))
            lowercoords.append(int(math.floor(x)))
        up_val = self.lookup(uppercoords)
        low_val = self.lookup(lowercoords)
        assert not (not up_val and low_val) #monotonicity check
        if up_val and low_val:
            return 'yes'
        elif (not up_val) and (not low_val):
            return 'no'
        elif up_val and (not low_val):
            return 'unknown'

        
t = Table([1,1,0,1],2,2)
assert t.lookup([0,1]) == 0
assert t.lookup([1,1]) == 1

t = Table([1,1,1,1,1,1,1,0],3,2)
assert t.lookup([1,1,1]) == 0

t = Table([0,1,1,1,1,1,1,1,1],2,3)
assert t.check_val([0.9,0.9]) == 'yes'
assert t.lookup([1,1,0]) == 1

t = Table([0,1,1,1],2,2)
assert t.check_val([0.5, 0.5]) == 'unknown'

t = Table([1,1,1,1],2,2)
assert t.check_val([0.5, 0.5]) == 'yes'

t = Table([0,1,1,1,1,1,1,1,1],2,3)
assert t.check_val([0.9, 0.9]) == 'yes'
assert t.check_val([0.1,0.1]) == 'unknown'

t = Table([1,1,1,1,1,1,1,1],3,2)
assert t.check_val([0.5,0.5,0.5]) == 'yes'
