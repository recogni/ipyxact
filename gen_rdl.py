#ipyxact example. Parses an IP-XACT XML file called generic_example.xml
#and prints out rdl or rdlp files for the register maps found
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
    parser.add_argument('-i', dest='inst_name', default="", help='Instance name for the addressmap')
    parser.add_argument('-p', dest='pfx_addr_map', default="", help='Prefix for names addressmap')
    parser.add_argument('-r', dest='ignore_rsvd_fld', default=0,  
                        help='0 = (default) parse all fields; 1 \
                               = Ignore fields that have "reserved" in their name')
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


def get_access_sw (access,modwriteval,type=""):
    if (type == "reg"):
        pre = "default "
    else:
        pre = ""

    rdl_access = ""
    if access == "read-only":
        rdl_access = pre + "sw = r"
    elif access == "read-write":
        if (modwriteval == "oneToClear"):
            rdl_access = pre + "sw = rw; woclr"
        else:
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

## some ipXact has reset fields under attribute "resets"
## while in some ipxact they are directly defined as "reset"
## Also some resets have mask and some done
## taking care of all these possibilities in the below code
def get_reset (f,reg,msb,lsb):
    width = msb - lsb + 1
    width_mask = pow(2,width) - 1
    is_mask_defined = 0
    is_reg_reset_defined = 0
    reg_has_resets = 0
    reg_has_reset = 0
    reg_has_reset_mask = 0
    fld_has_resets = 0
    fld_has_reset = 0
    try:
        reg.resets # does a exist in the current namespace
    except AttributeError:
        reg_has_resets = 0
    else:
        reg_has_resets = (reg.resets != None)
        try:
            reg.resets.reset.mask # does a exist in the current namespace
        except AttributeError:
            reg_has_reset_mask = 0
        else:
            reg_has_reset_mask = (reg.resets.reset.mask != None)
    
    
    try:
        reg.reset # does a exist in the current namespace
    except AttributeError:
        reg_has_reset = 0
    else:
        reg_has_reset = (reg.reset != None)
        try:
            reg.reset.mask # does a exist in the current namespace
        except AttributeError:
            reg_has_reset_mask = 0
        else:
            reg_has_reset_mask = (reg.reset.mask != None)
    
    try:
        f.reset # does a exist in the current namespace
    except AttributeError:
        fld_has_reset = 0
    else:
        fld_has_reset = (f.reset != None)
    
    try:
        f.resets # does a exist in the current namespace
    except AttributeError:
        fld_has_resets = 0
    else:
        fld_has_resets = (f.resets != None)
    
    
    if (reg_has_resets):
        reg_reset = reg.resets.reset.value
        is_reg_reset_defined = 1
        if (reg_has_reset_mask):
            reset_mask = reg.resets.reset.mask
            is_mask_defined = 1
    elif (reg_has_reset):
        reg_reset = reg.reset.value
        is_reg_reset_defined = 1
        if (reg_has_reset_mask):
            reset_mask = reg.reset.mask
            is_mask_defined = 1
    ## if a field has an explicit reset attribute defined, use that
    reset = "na"
    if (fld_has_reset): 
        reset = f.reset.value
    elif (fld_has_resets):
        reset = f.resets.reset.value
    elif (is_reg_reset_defined):
        reset = (reg_reset >> lsb) & width_mask
        if (is_mask_defined):
            fmask = (reset_mask >> lsb) & width_mask
            if (fmask == 0):
                reset = "na"
            else:
                reset = reset & fmask
    return reset


def write_reg_fields(reg, indent, is_rdlp, ignore_rsvd_kw):
    indent2 = indent + "   "
    lsb = 0
    msb = 0
    num_fld_op = 0
    for f in sorted(reg.field, key=lambda x: x.bitOffset):
        if (f.description) :
            desc = f.description
            desc = desc.encode("utf-8")
            desc = desc.decode("ascii","ignore")
            desc = desc.replace ("\"","'")
        else :
            desc = f.name
        lsb = f.bitOffset
        msb = f.bitOffset + f.bitWidth - 1
        if ("reserved" in f.name.lower() and ignore_rsvd_kw):
            of.write(f"{indent} // Field {f.name} has \"reserved\" as part of its name and hence ignored\n")
        else:
            of.write(f"{indent} field {{\n")
            of.write(f"{indent2} name = \"{f.name.lower()}\";\n")
            of.write(f"{indent2} desc = \"{desc}\";\n")
            reset = get_reset(f,reg,msb,lsb)
            if (reset != "na"):
                of.write(f"{indent2} reset = {hex(reset)};\n")
            of.write(f"{indent2} {get_access_sw(f.access,f.modifiedWriteValue)};\n")
            #of.write(f"{indent2} {get_access_hw(f.access)};\n")
            of.write(f"{indent} }} {get_item_name(f.name, is_rdlp)}[{msb}:{lsb}];\n")
            num_fld_op = num_fld_op+1
    return num_fld_op

def is_rdl_keyword (name):
    ## this is not an exhaustive list of rdl keywords but only
    ## a small subset that are currently causing issues
    kw_list = ["reset","enable","type"]
    if name in kw_list :
        return 1
    else:
        return 0

def get_item_name (name,is_rdlp):
    if (is_rdl_keyword(name.lower())):
        new_name = name.upper()
    else:
        new_name = name.lower()
    return new_name

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
            mname=name.lower()
        else:
            mname = m.name.lower()
        if (args.pfx_addr_map):
            mname = args.pfx_addr_map + "_" + mname
        of.write(f"addrmap {mname} {{\n")
        multiblock = len(m.addressBlock) > 1
        for block in m.addressBlock:
            if multiblock:
                bname = mname + '_' + block.name.lower()
            else:
                bname = mname
            of.write(f"{indent} regfile {{\n")
            for reg in sorted(block.register, key=lambda a: a.addressOffset):
                of.write(f"{indent2} reg {{\n")
                of.write(f"{indent3} regwidth = {reg.size};\n")
                if (reg.access):
                    of.write(f"{indent3} default {get_access_sw(reg.access,'',reg)};\n")
                    #of.write(f"{indent3} default {get_access_hw(reg.access,reg)};\n")
                if reg.field:
                    num_fld_op = write_reg_fields(reg, indent3, add_pre, args.ignore_rsvd_fld)
                    ## if all the fields in a reg are reserved then there will be no fields output in rdlp
                    ## this can lead to some bad things later on in the tool flow like xml2c scripts
                    ## Hence if all the fields in a reg are reserved fields, then add one reserved field 
                    ## equal to the size of the register to keep downstream tools happy

                    if (num_fld_op == 0):
                        of.write(f"{indent3} field {{\n")
                        of.write(f"{indent4} name = \"reserved\";\n")
                        of.write(f"{indent4} desc = \"reserved field added because no fields were defined for this reg\";\n")
                        of.write(f"{indent4} reset = 0;\n")
                        of.write(f"{indent4} sw = r;\n")
                        #of.write(f"{indent4} hw = w;\n")
                        of.write(f"{indent3} }} rsvd[{reg.size-1}:0];\n")
                of.write(f"{indent2} }} {get_item_name(reg.name,add_pre)} {add_pre}{hex(reg.addressOffset)};\n\n")
            of.write(f"{indent} }} {get_item_name(block.name, add_pre)} {add_pre}{hex(block.baseAddress)};\n\n")
        of.write(f"}} {args.inst_name};\n")

def remove_non_ascii(s):
    return "".join(c for c in s if ord(c)<128)

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
