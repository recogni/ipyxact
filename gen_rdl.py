#ipyxact example. Parses an IP-XACT XML file called generic_example.xml
#and prints out a C header of the register maps found
import argparse
import sys
import time
import os

from ipyxact.ipyxact import Component

def parse_args():
    parser = argparse.ArgumentParser(
            description='Generate a rdl/rdlp from an IP-XACT file')
    parser.add_argument('ipxact_file', help='IP-XACT file to parse')
    parser.add_argument('-o', dest='output_file', help='Write output to file')
    parser.add_argument('-i', dest='inst_name', help='Instance name for the addressmap')
    return parser.parse_args()

def open_output(output):
    return open(output, 'w') if output else sys.stdout

def write_prologue(of):
    of.write('// ----------------------------------------------------------------\n')
    of.write('// RDL(p) file generated from IP-Xact xml file using ipxact/gen_rdl.py\n')
    of.write('// Do not edit\n')
    of.write('// ----------------------------------------------------------------\n')
    of.write('\n')
    of.write('\n')


def get_access_sw (access,type=""):
    if (type == "reg"):
        pre = "default "
    else:
        pre = ""

    rdl_access = ""
    if access == "read-only":
        rdl_access = pre + "sw = r"
    elif access == "read-write":
        rdl_access = pre + "sw = rw"
    elif access == "write-only":
        rdl_access = pre + "sw = w"
    else:
        print ("ERROR: Access type unsupported")
        sys.exit(0)
    return rdl_access

def get_access_hw (access,type=""):
    if (type == "reg"):
        pre = "default "
    else:
        pre = ""

    rdl_access = ""
    if access == "read-only":
        rdl_access = pre + "hw = w"
    elif access == "read-write":
        rdl_access = pre + "hw = r"
    elif access == "write-only":
        rdl_access = pre + "hw = r"
    else:
        print ("ERROR: Access type unsupported")
        sys.exit(0)
    return rdl_access


def get_reset (ds,type):
    if (type == "field"):
        ## this is a reset at field level
            reset = ds.resets.reset.value
    else:
        ## this is a reset at register level
        reset = ds.reset.value
    return reset


def write_reg_fields(reg, indent):
    indent2 = indent + "   "
    lsb = 0
    msb = 0
    for f in sorted(reg.field, key=lambda x: x.bitOffset):
        if (f.description) :
            desc = f.description
            desc = desc.replace ("\"","'")
        else :
            desc = f.name
        lsb = f.bitOffset
        msb = f.bitOffset + f.bitWidth - 1 
        of.write(f"{indent} field {{\n")
        of.write(f"{indent2} name = \"{f.name}\";\n")
        of.write(f"{indent2} desc = \"{desc}\";\n")
        if (f.resets):
            of.write(f"{indent2} reset = {hex(get_reset(f,'field'))};\n")
        of.write(f"{indent2} {get_access_sw(f.access)};\n")
        of.write(f"{indent2} {get_access_hw(f.access)};\n")
        of.write(f"{indent} }} {f.name}[{msb}:{lsb}];\n")

def write_memory_maps(of, memory_maps, offset=0, name=None):
    indent = "    "
    indent2 = indent+indent
    indent3 = indent+indent+indent
    indent4 = indent2+indent2
    filename, ext = os.path.splitext(args.output_file)
    if (ext == ".rdlp"): 
        add_pre = "\@"
    else:
        add_pre = "@"
    for m in memory_maps.memoryMap:
        if name:
            mname=name.upper()
        else:
            mname = m.name.upper()
        of.write(f"addrmap {mname} {{\n")
        multiblock = len(m.addressBlock) > 1
        for block in m.addressBlock:
            if multiblock:
                bname = mname + '_' + block.name.upper()
            else:
                bname = mname
            of.write(f"{indent} regfile {{\n")
            for reg in sorted(block.register, key=lambda a: a.addressOffset):
                of.write(f"{indent2} reg {{\n")
                of.write(f"{indent3} regwidth = {reg.size};\n")
                if (reg.reset):
                    of.write(f"{indent3} default reset = {hex(get_reset(reg,reg))};\n")
                if (reg.access):
                    of.write(f"{indent3} default {get_access_sw(reg.access,reg)};\n")
                    of.write(f"{indent3} default {get_access_hw(reg.access,reg)};\n")
                if reg.field:
                    write_reg_fields(reg, indent3)
                of.write(f"{indent2} }} {reg.name} {add_pre}{hex(reg.addressOffset)};\n\n")
            of.write(f"{indent} }} {block.name} {add_pre}{hex(block.baseAddress)};\n\n")
        of.write(f"}} {args.inst_name};")


if __name__ == '__main__':
    args = parse_args()
    with open(args.ipxact_file) as f:
        name = None
        offset = 0

        component = Component()
        component.load(f)

        with open_output(args.output_file) as of:
            write_prologue(of)
            write_memory_maps(of, component.memoryMaps, offset, name)
