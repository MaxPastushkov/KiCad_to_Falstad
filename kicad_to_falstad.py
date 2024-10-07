#!/usr/bin/env python

from skip import Schematic
import math
import sys

HEADER = "$ 3 0.000005 10.20027730826997 50 5 43 5e-11"
scale = 8 / 1.27

def round_sig(x, sig):
	return round(x, sig-int(math.floor(math.log10(abs(x))))-1)

def printerr(err):
	sys.stderr.write(err + '\n')

def handle_value(value_str):
	
	if len(value_str) > 2 and value_str[-2:-1].isalpha():
		# Part has units at the end (ex. mH)
		value_str = value_str[:-1]
		
	c = value_str[-1:]
	
	if c.isnumeric():
		value = float(value_str)
	else:
		
		base = float(value_str[:-1])
		
		if c == 'p':
			value = base * 1e-12
		elif c == 'n':
			value = base * 1e-9
		elif c == 'u':
			value = base * 1e-6
		elif c == 'm':
			value = base * 1e-3
		elif c == 'k':
			value = base * 1e3
		elif c == 'M':
			value = base * 1e6
		elif c == 'G':
			value = base * 1e9
		else:
			value = base
	
	return round_sig(value, 5) # Temporary


# Round, scale, and format coordinate list
def coords(inp):
	if type(inp) != list:
		return round(inp * scale)
	return str(round(inp[0] * scale)) + " " + str(round(inp[1] * scale))

# Account for all 16 ways a transistor can be oriented
def process_transistors(comp, structure, transistor_type):

	if transistor_type == "BJT":
		C_loc = comp.pin.C.location.value
		E_loc = comp.pin.E.location.value
		B_loc = comp.pin.B.location.value
	elif transistor_type in ["MOSFET", "JFET"]:
		C_loc = comp.pin.D.location.value
		E_loc = comp.pin.S.location.value
		B_loc = comp.pin.G.location.value
	
	# We need to make a little wire since Falstad transistors are smaller
	end_loc = [0, 0]
	
	if comp.at[2] in [0, 180]: # If horizontal
		
		end_loc[0] = C_loc[0]
		end_loc[1] = B_loc[1]
		
		pin_loc = 1
		if C_loc[1] > E_loc[1]: # If collector is below emitter
			pin_loc = -1
			
		print("w {0} {1} {2} 0".format(coords(C_loc), coords(end_loc[0]), coords(end_loc[1]) - (16 * pin_loc)))
		print("w {0} {1} {2} 0".format(coords(E_loc), coords(end_loc[0]), coords(end_loc[1]) + (16 * pin_loc)))
		
		
	elif comp.at[2] in [90, 270]: # If vertical
		
		# Fix weird edge cases
		if ((comp.at[2] == 90 and C_loc[0] > E_loc[0])
			or (comp.at[2] == 270 and C_loc[0] < E_loc[0])):
			
			# Reflect E and C positions over the component center
			for loc in [E_loc, C_loc, B_loc]:
				dx = comp.at.value[0] - loc[0]
				dy = comp.at.value[1] - loc[1]
				loc[0] += 2 * dx
				loc[1] += 2 * dy
		
		end_loc[0] = B_loc[0]
		end_loc[1] = C_loc[1]
		
		pin_loc = 1
		if C_loc[0] > E_loc[0]: # If collector is to the right of emitter
			pin_loc = -1
			
		print("w {0} {1} {2} 0".format(coords(C_loc), coords(end_loc[0]) - (16 * pin_loc), coords(end_loc[1])))
		print("w {0} {1} {2} 0".format(coords(E_loc), coords(end_loc[0]) + (16 * pin_loc), coords(end_loc[1])))
		
	else:
		printerr("Warning: Invalid orientation for " + comp.Reference.value)
		return
	
	swap = 0
	# Set swap flag if needed
	if structure in [1, 32]: # NPN, NMOS
		if comp.at[2] == 90       and C_loc[0] < E_loc[0]: swap = 1
		if comp.at[2] in [0, 180] and C_loc[1] > E_loc[1]: swap = 1
	else:                    # PNP, PMOS
		if comp.at[2] == 270      and C_loc[0] > E_loc[0]: swap = 1
		if comp.at[2] == 0        and C_loc[1] < E_loc[1]: swap = 1
	
	if transistor_type == "BJT":
		print("t {0} {1} {2} {3} 0 0 100 default".format(coords(B_loc), coords(end_loc), swap, structure))
	elif transistor_type == "MOSFET":
		print("f {0} {1} {2} 1.5 0.02".format(coords(B_loc), coords(end_loc), structure | (swap << 3)))
	elif transistor_type == "JFET":
		print("j {0} {1} {2} -4 0.00125".format(coords(B_loc), coords(end_loc), structure | (swap << 3)))

if len(sys.argv) < 2:
	printerr("Usage: " + sys.argv[0] + " [path to .kicad_sch file]")
	sys.exit(-1)

sch = Schematic(sys.argv[1])

print(HEADER)

# Add all wires
for wire in sch.wire:
	print("w {0} {1} 0".format(coords(wire.start.value), coords(wire.end.value)))

supported_types = ['R', 'C', 'L', 'Q', 'D', '#PWR', 'U', 'SW']
for comp_type in supported_types:
	comps = sch.symbol.reference_startswith(comp_type)
	for comp in comps:
		
		if comp_type == 'R' and len(comp.pin) == 2:
			print("r {0} {1} 0 {2}".format(coords(comp.pin[0].location.value), coords(comp.pin[1].location.value), handle_value(comp.Value.value)))
			
		elif comp_type == 'C':
			print("c {0} {1} 0 {2} 0 0.001".format(coords(comp.pin[0].location.value), coords(comp.pin[1].location.value), handle_value(comp.Value.value)))
			
		elif comp_type == 'L':
			print("l {0} {1} 0 {2} 0 0".format(coords(comp.pin[0].location.value), coords(comp.pin[1].location.value), handle_value(comp.Value.value)))
			
		elif comp_type == 'Q':
			if "NPN" in comp.lib_id.value:
				structure = 1
				transistor_type = "BJT"
			elif "PNP" in comp.lib_id.value:
				structure = -1
				transistor_type = "BJT"
			elif "NMOS" in comp.lib_id.value:
				structure = 32
				transistor_type = "MOSFET"
			elif "PMOS" in comp.lib_id.value:
				structure = 33
				transistor_type = "MOSFET"
			elif "NJFET" in comp.lib_id.value:
				structure = 32
				transistor_type = "JFET"
			elif "PJFET" in comp.lib_id.value:
				structure = 33
				transistor_type = "JFET"
			else:
				printerr("Warning: Unknown transistor type: " + comp.lib_id.value)
				continue
			
			process_transistors(comp, structure, transistor_type)
			
		elif comp_type == "D":
			A_loc = comp.pin.A.location.value
			K_loc = comp.pin.K.location.value
			if ((comp.at[2] == 270 and A_loc[1] < K_loc[1]) # More edge cases
				or (comp.at[2] == 90 and A_loc[1] > K_loc[1])):
				print("d {0} {1} 2 default".format(coords(K_loc), coords(A_loc)))
			else:
				print("d {0} {1} 2 default".format(coords(A_loc), coords(K_loc)))
		
		elif comp_type == "#PWR":
			if comp.Value.value == "GND":
				print("g {0} {1} {2} 0 0".format(coords(comp.at.value), coords(comp.at.value[0]), coords(comp.at.value[1]) + 16))
			else:
				val = comp.Value.value[:-1] # Strip V
				print("R {0} {1} {2} 0 0 40 {3} 0 0 0.5".format(coords(comp.at.value), coords(comp.at.value[0]), coords(comp.at.value[1]) - 16, handle_value(val)))
		
		elif comp_type == "U":
			if "Amplifier_Operational" in comp.lib_id.value:
				inv_loc = []
				noninv_loc = []
				out_loc = []
				for pin in comp.pin:
					if pin.name == "-":
						inv_loc = pin.location.value
					elif pin.name == "+":
						noninv_loc = pin.location.value
					elif pin.name == "~":
						out_loc = pin.location.value
					else:
						printerr("Warning: Unknown opamp pin: " + pin.name)
				
				if not inv_loc or not noninv_loc or not out_loc:
					continue
				
				inp_midpoint = [(inv_loc[0] + noninv_loc[0]) / 2, (inv_loc[1] + noninv_loc[1]) / 2]
				
				if inp_midpoint[1] - out_loc[1] < 0.01: # Horizontal
					
					if inv_loc[1] < noninv_loc[1]: # Non-inverting is above
						swap = 0
					else:
						swap = 1
					
					print("w {0} {1} {2} 0".format(coords(inv_loc), coords(inv_loc[0]), coords(inv_loc[1]) - (8 * (2 * swap - 1))))
					print("w {0} {1} {2} 0".format(coords(noninv_loc), coords(noninv_loc[0]), coords(noninv_loc[1]) + (8 * (2 * swap - 1))))
					
				else:
					printerr("Warning: Ignoring vertical opamp " + comp.Reference.value)
					continue
				
				print("a {0} {1} {2} 12 -12 1000000 0 0 100000".format(coords(inp_midpoint), coords(out_loc), 10 + swap))
		
		elif comp_type == "R" and "Potentiometer" in comp.lib_id.value:
			loc_1 = comp.pin.n1.location.value
			loc_2 = comp.pin.n2.location.value
			loc_3 = comp.pin.n3.location.value
			
			corner_1 = [loc_2[0], loc_3[1]]
			corner_2 = [loc_3[0], loc_2[1]]
			
			# Determine which one is the actual corner
			if math.dist(corner_1, comp.at.value[:-1]) < 0.01:
				corner = corner_2
			else:
				corner = corner_1
			
			print("174 {0} {1} 1 {2} 0.5 {3}".format(coords(loc_1), coords(corner), handle_value(comp.Value.value), comp.Reference.value))
		
		elif comp_type == "SW" and "SPDT" in comp.lib_id.value:
			loc_1 = comp.pin.A.location.value
			loc_2 = comp.pin.B.location.value
			loc_3 = comp.pin.C.location.value
			midpoint = [(loc_1[0] + loc_3[0]) / 2, (loc_1[1] + loc_3[1]) / 2]
			
			print("S {0} {1} 0 0 false 0 2".format(coords(loc_2), coords(midpoint)))
