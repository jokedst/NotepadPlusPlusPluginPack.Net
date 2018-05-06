# requires the notepad++ project is cloned in a folder next to this plugin pack 

import Face
from FileGenerator import Regenerate

indent = "        "

def printLexCSFile(f):
	out = []
	for name in f.order:
		v = f.features[name]
		if v["Value"] == "-1": v["Value"] = "0xFFFFFFFF"
		if v["FeatureType"] in ["fun", "get", "set"]:
			if "Comment" in v: out.extend(["        /// " + line for line in v["Comment"]])
			featureDefineName = "SCI_" + name.upper()
			out.append(indent + featureDefineName + " = " + v["Value"] + ",")
			out.append("")
		elif v["FeatureType"] in ["evt"]:
			featureDefineName = "SCN_" + name.upper()
			if "Comment" in v: out.extend(["        /// " + line for line in v["Comment"]])
			out.append(indent + featureDefineName + " = " + v["Value"] + ",")
			out.append("")
		elif v["FeatureType"] in ["val"]:
			if not ("SCE_" in name or "SCLEX_" in name):
				if "Comment" in v: out.extend(["        /// " + line for line in v["Comment"]])
				out.append(indent + name + " = " + v["Value"] + ",")
				out.append("")
	out[-1] = out[-1][:-1] # drop the very last comma of the last line
	return out

def isTypeUnsupported(t):
	if t in ["formatrange"]: return True
	return False

def translateType(t):
	if t == "cells": return "Cells"
	if t == "colour": return "Colour"
	if t == "position": return "Position"
	if t == "textrange": return "TextRange"
	if t == "findtext": return "TextToFind"
	if t == "keymod": return "KeyModifier"
	return t

def translateVariableAccess(name, type):
	if type == "bool": return name + " ? 1 : 0"
	if type in ["string", "stringresult", "Cells"]: return "(IntPtr) " +name+ "Ptr"

	res = name if name else "Unused"
	if type in ["Colour", "Position", "KeyModifier"]:
		res += ".Value"
	if type in ["TextRange", "TextToFind"]: 
		res += ".NativePointer"
	return res

def methodName(name):
	return name

def appendComment(indent, out, v):
	if "Comment" in v: 
		if len (v["Comment"]) == 1: 
			out.append(indent + "/// <summary>" + v["Comment"][0] + " (Scintilla feature " + v["Value"] + ")</summary>")
		else:
			out.append(indent + "/// <summary>")
			out.extend([indent + "/// " + line for line in v["Comment"]])
			out.append(indent + "/// (Scintilla feature " + v["Value"] + ")")
			out.append(indent + "/// </summary>")

def getUnsafeModifier(returnType, param1Type, param2Type):
	if "string" in [returnType, param1Type, param2Type]:
		return "unsafe "
	if "Cells" in [returnType, param1Type, param2Type]:
		return "unsafe "
	return ""


def translateReturnType(v, name):
	if v["Param1Type"] == "stringresult" or v["Param2Type"] == "stringresult": 
		return "string" 
	elif name.startswith("Get") and (name.endswith("Pointer") or name == "GetDirectFunction"):
		return "IntPtr"
	else:
		return translateType(v["ReturnType"])

def translateParameterType(name, type):
	if name == "pointer" and type == "int":
		return "IntPtr"
	else:
		return translateType(type)

def getParameterList(param1Type, param1Name, param2Type, param2Name):
	first  = param1Type + " " + param1Name if param1Type and param1Type != "stringresult" else ""
	second = param2Type + " " + param2Name if param2Type and param2Type != "stringresult" else ""
	separator = ", " if first and second else ""
	return first + separator + second

#def printEnumDefinitions(f):
#	out = []
#	for name in f.order:
#		v = f.features[name]
#
#		iindent = indent + "    "
#
#		if v["FeatureType"] in ["enu"]:
#			appendComment(indent, out, v)
#			prefix = v["Value"]
#			out.append(indent + "public enum " + name)
#			out.append(indent + "{")
#			for ename in f.order:
#				ve = f.features[ename]
#				if ve["FeatureType"] in ["val"]:
#					if ename.startswith(prefix):
#						out.append(iindent + ename[len(prefix):] + " = " + ve["Value"] + "," )
#
#			out.append(indent + "}")
#	return out

def printLexGatewayFile(f):
	out = []
	for name in f.order:
		v = f.features[name]

		iindent = indent + "    "

		if v["FeatureType"] in ["fun", "get", "set"]:
			param1Type = translateParameterType(v["Param1Name"], v["Param1Type"])
			param1Name = v["Param1Name"]
			param2Type = translateParameterType(v["Param2Name"], v["Param2Type"])
			param2Name = v["Param2Name"]
			returnType = translateReturnType(v, name)

			if (isTypeUnsupported(param1Type) or isTypeUnsupported(param2Type) or isTypeUnsupported(returnType)):
				continue

			appendComment(indent, out, v)

			featureConstant = "SciMsg.SCI_" + name.upper()

			out.append(indent + "public " 
				+ getUnsafeModifier(returnType, param1Type, param2Type) 
				+ returnType + " " 
				+ methodName(name) 
				+ "(" + getParameterList(param1Type, param1Name, param2Type, param2Name) +")")
			out.append(indent + "{")

			if param1Type == "string":
				out.append(iindent + "fixed (byte* "+param1Name+"Ptr = Encoding.UTF8.GetBytes(" +param1Name+ "))")
				out.append(iindent + "{")
				iindent = iindent + "    "

			if param2Type == "string":
				out.append(iindent + "fixed (byte* "+param2Name+"Ptr = Encoding.UTF8.GetBytes(" +param2Name+ "))")
				out.append(iindent + "{")
				iindent = iindent + "    "

			if param1Type == "Cells":
				out.append(iindent + "fixed (char* "+param2Name+"Ptr = "+param1Name+".Value)")
				out.append(iindent + "{")
				iindent = iindent + "    "

			if param2Type == "Cells":
				out.append(iindent + "fixed (char* "+param2Name+"Ptr = "+param2Name+".Value)")
				out.append(iindent + "{")
				iindent = iindent + "    "

			bufferSize = "10000"
			if (param1Type == "int" and param1Name == "length") or (param2Type == "int" and param2Name == "length"): 
				bufferSize = "length"
			
			bufferVariableName = ""
			if param1Type == "stringresult":
				bufferVariableName = param1Name + "Buffer"
				out.append(iindent + "byte[] " + bufferVariableName +" = new byte[" + bufferSize + "];")
				out.append(iindent + "fixed (byte* "+param1Name+"Ptr = " +bufferVariableName + ")" )
				out.append(iindent + "{")
				iindent = iindent + "    "
				
			if param2Type == "stringresult":
				bufferVariableName = param2Name + "Buffer"
				out.append(iindent + "byte[] " + bufferVariableName +" = new byte[" + bufferSize + "];")
				out.append(iindent + "fixed (byte* "+param2Name+"Ptr = " +bufferVariableName + ")" )
				out.append(iindent + "{")
				iindent = iindent + "    "
				
			firstArg = translateVariableAccess(param1Name, param1Type)
			seconArg = translateVariableAccess(param2Name, param2Type)

			out.append(iindent + "IntPtr res = Win32.SendMessage(scintilla, " +featureConstant+ ", " +firstArg+ ", " +seconArg+ ");")


			if returnType != "void":
				if returnType == "bool":
					out.append(iindent + "return 1 == (int) res;")
				elif returnType == "Colour":
					out.append(iindent + "return new Colour((int) res);")
				elif returnType == "Position":
					out.append(iindent + "return new Position((int) res);")
				elif returnType == "string":
					out.append(iindent + "return Encoding.UTF8.GetString("+bufferVariableName+").TrimEnd('\\0');")
				else:
					out.append(iindent + "return (" +returnType+ ") res;")

			if param1Type in ["string", "Cells", "stringresult"]:
				iindent = iindent[4:]
				out.append(iindent + "}")
			if param2Type in ["string", "Cells", "stringresult"]:
				iindent = iindent[4:]
				out.append(iindent + "}")

			out.append(indent + "}")
			out.append("")
	return out

def printLexIGatewayFile(f):
	out = []
	for name in f.order:
		v = f.features[name]

		if v["FeatureType"] in ["fun", "get", "set"]:
			param1Type = translateParameterType(v["Param1Name"], v["Param1Type"])
			param1Name = v["Param1Name"]
			param2Type = translateParameterType(v["Param2Name"], v["Param2Type"])
			param2Name = v["Param2Name"]
			returnType = translateReturnType(v, name)

			if (isTypeUnsupported(param1Type) or isTypeUnsupported(param2Type) or isTypeUnsupported(returnType)):
				continue

			appendComment(indent, out, v)

			out.append(indent + getUnsafeModifier(returnType, param1Type, param2Type) 
				+ returnType + " " 
				+ methodName(name) 
				+ "(" + getParameterList(param1Type, param1Name, param2Type, param2Name) +");")

			out.append("")
	return out


def main():
	f = Face.Face()
	f.ReadFromFile("../../../notepad-plus-plus/scintilla/include/Scintilla.iface")
	Regenerate("../../Visual Studio Project Template C#/PluginInfrastructure/Scintilla_iface.cs", "/* ", printLexCSFile(f))
	Regenerate("../../Visual Studio Project Template C#/PluginInfrastructure/ScintillaGateWay.cs", "/* ", printLexGatewayFile(f))
	Regenerate("../../Visual Studio Project Template C#/PluginInfrastructure/IScintillaGateWay.cs", "/* ", printLexIGatewayFile(f))
#	Regenerate("../../Visual Studio Project Template C#/PluginInfrastructure/gatewaydomain.cs", "/* ", printEnumDefinitions(f))


if __name__ == "__main__":
	main()
