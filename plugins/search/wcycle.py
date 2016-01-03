def main():
    w = open('builtins/search/wolfram.txt').read()
    nc = open('builtins/search/cyclenumber.txt').read()
    nci = int(nc)
    wf = int(w) - 1
    wn = open('builtins/search/wolfram.txt', 'w')
    wn.write(str(wf))
    if wf == 0:
        c = open('builtins/search/appid.txt').read()
        print c
        c = c.split("\n")
        print c
        ln = c[-1].split('=')[0]
        global k
        print ln
        print nci
        if nci == int(ln):
            cvar = True
            k = c[0].split('=')[1]

        else:
            kvar = False
            for item in c:
                n = item.split('=')
                if int(n[0]) == nci + 1:
                    k = n[1]
        i = open('builtins/search/appidfinal.txt', 'w')
        i.write(k)
        cn = open('builtins/search/cyclenumber.txt', 'w')
        if cvar == False:
            cn.write(str(nci + 1))
        elif cvar == True:
            cn.write(str(1))
        wn.close()
        wnf = open("builtins/search/wolfram.txt", 'w')
        wnf.write('2000')
