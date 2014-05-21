#!/usr/bin/env python
'''
Created on 28 jan 2014

@author: bernerus
'''
import sys


def template2keys(template, indent=1):
    #print >>sys.stderr, "    " * indent + "Template2keys: template=", template, "indent=", indent
    kvtuples = []
    ltemplate = template
    for k in ltemplate.split(","):
        if k:
            k = k.strip()
        if k.startswith('{'): 
            k = k[1:]
        if k.endswith('}'):
            k = k[:-1]
        #print >>sys.stderr, "    " * indent + "splitting:", k
        try:
            (key, val) = k.split(":", 1)
        except ValueError:
            print >>sys.stderr, "Invalid value:", k
            raise
        if key.startswith('"') or key.startswith("'"):
            key = key[1:]
        if key.endswith('"') or key.endswith("'"):
            key = key[:-1]
        kvtuples.append((key, val))
    #print >>sys.stderr, "    " * indent + "Template2keys: kvtuples=", kvtuples
    return kvtuples


def print_struct_in_order(x, kvtuples, template, output, indent=1):
    #print >>sys.stderr, "    " * indent + "print_struct_in_order: x=", x, "kvtuples=", kvtuples, "template=", template, "indent=", indent
    values = []
    for kvtuple in kvtuples:
        key = kvtuple[0]
        if key.startswith('_'):
            continue
        keyval = kvtuple[1].strip()
        if keyval == "False":  # Hmm, this is probably not supported
            raise ValueError("Never use False as a value to _dig or _fetch functions")
        if keyval == "True":
            if x[key]:
                if type(x[key]) is list:
                    values.append(x[key])
                else:
                    values.append(unicode(x[key]))
            else:
                values.append("NULL")
        else:
            print_object_in_template_order(x[key], keyval, output, indent=indent + 1)
            output.write(" \t")
    #print >>sys.stderr, "VALUES=", values
    if len(values) == 1 and type(values[0]) is list:
        #print >>sys.stderr ,"LIST=", values[0]
        output.write("\n".join(values[0]))
    else:  
        output.write(" \t".join(values))
    
    
def print_object_in_template_order(obj, template, output, indent=1):
    #print >>sys.stderr, "    " * (indent - 1) + "  " + "print_object_in_template_order: obj=", obj, "template=", template, "indent=", indent
    if type(obj) is list:
        for o in obj:
            print_object_in_template_order(o, template, output, indent + 1)
            print >>output
    else:
        kvtuples = template2keys(template, indent)
        print_struct_in_order(obj, kvtuples, template, output, indent=indent)
 
 
def process(command, output):
    res = None
    (cmd, sep, arg) = command.partition("(")
    #print >>sys.stderr, cmd, sep, arg
    arg = arg.strip()
    if sep:
        arg = arg.rstrip(")")
    #print >>sys.stderr, cmd, sep, arg
    global srv
    
    args = arg.split(",", 1)
    
    try:
        if not srv:
            srv = rpcc_client.RPCC("https://adhoc.ita.chalmers.se:8877")
        
        s = cmd + "(" + ",".join(args) + ")"
        
        #print >> sys.stderr, "CMD=%s" % cmd
        #print >> sys.stderr, "EXEC: %s" % s
        try:
            exec s
        except (rpcc_client.RPCCValueError,rpcc_client.RPCCLookupError,rpcc_client.RPCCRuntimeError,rpcc_client.RPCCTypeError) as e:
            e=e[0]
            try:
                if e["value"]:
                    print >>sys.stderr, "%s: %s" % (e.desc, e.value)
                else:
                    print >>sys.stderr, "%s" % e.desc
            except:
                print >>sys.stderr, "Unexpected error from server:", e
            return 1
             
        except Exception:
            #print >>sys.stderr, "Exception on command:", s
            raise
        #print >> sys.stderr, "RES=%s" % res
        s = ""
        if cmd.endswith("_dig") or cmd.endswith("_fetch"):
            #print >>sys.stderr, "ARGS1=", args[1]
            print_object_in_template_order(res, args[1], output)
            #print >>sys.stderr, output.getvalue().rstrip('\n')
            
            #print >>sys.stderr, "OBJECT VAL='" + output.getvalue() + "'"
            return 0
                
        if type(res) is unicode or type(res) is str:
            s = res
            
        if type(res) is not None:  
            output.write(s)
            
        print output.getvalue().rstrip('\n')
        #print >>sys.stderr, "OBJECT VALUE='" + output.getvalue()+"'"
        return 0
            
    except KeyError, e:
        print >> sys.stderr, e
        try:
            print >> sys.stderr, "ERROR: %s: %s" % (e[0].desc, e[0].value)
        except:
            print >> sys.stderr, "ERROR:", e
        return 1
    
    
import os
import StringIO
srv = None
import rpcc_client

fifo_in = sys.argv[1]
fifo_out = sys.argv[2]

update_template = {}  # For use by dhcp2
options = {}  # For use by dhcp2

while True:
        fin = open(fifo_in, "r")
        fout = open(fifo_out, "w")
        sys.stdout = fout
        #print >>sys.stderr, fin
        finval = fin.read()
        #print >>sys.stderr, "Finval=", finval
        output = StringIO.StringIO()
        process(finval, output)
        print output.getvalue().rstrip("\n").encode("utf-8")
        #print >>sys.stderr, output.getvalue().rstrip("\n")
        sys.stdout.flush()
        fout.close()
        fin.close()
