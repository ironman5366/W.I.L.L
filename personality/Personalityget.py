from datetime import datetime
import os
import random
greetfile = open("personality/personality.txt").read()
greetings = greetfile.split('\n')
def get_greet(f):
    #Get time and determine environmental variables
    t = str(datetime.now()) 
    tt = t.split(' ')
    ttt = tt[1].split(':')
    tf = int(ttt[0])
    if tf < 12:
        lt = "Morning"
    elif tf > 17:
        lt = "Night"
    else:
        lt = "Afternoon"    

    #Open the file with the string to output
    o = open("personality/output.txt").read()
    ol = o.split('\n')
    olpn = int(ol[0].split('polite=')[1])
    olhn = int(ol[1].split('humor=')[1])
    p = []
    print greetings
    for l in greetings:
        try:
            v = l.split(':')[1]
            k = l.split(':')[0]
            vf = v.split(',')
            if vf[0] == lt or vf[0] == 'Neutral':
                vfp = vf[1].split(';')
                vfpn = int(vfp[0].split('polite=')[1])
                if olpn == vfpn or olpn == vfpn-1 or olpn == vfpn+1 or olpn == vfpn-2 or olpn == vfpn+2:
                    vfh = vfp[1].split('/')
                    vfph = int(vfh[0].split('humor=')[1])
                    if olhn == vfph or olhn == vfph-1 or olhn == vfhn+1 or olph == vfhn-2 or olph == vfph+2:
                        vfhf = vfh[1].split('f=')[1]
                        if vfhf == f:
                            p.append(k)
                        else:
                            pass
                    else:
                        pass
                else:
                    pass
            else:
                pass
        except IndexError:
            pass
    finalout = random.choice(p)
    return "greeting:;:;:"+finalout
