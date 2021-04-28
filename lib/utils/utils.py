###################################
###     All utils functions     ###
###################################

def human_format(num):
    # have to do times 1000 because we are looking at kWh and not Wh
    num = num*1000
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # add more suffixes if you need them
    return '%.2f%s' % (num, [' Wh', ' kWh', ' mWh', ' gWh', ' tWh', ' pWh'][magnitude])