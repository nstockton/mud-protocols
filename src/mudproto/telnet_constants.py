"""
Telnet Constants.

Definitions for various command and option negotiation bytes.

---
ASCII Definitions

Attributes:
	NULL: No operation.
	BEL: Produces an audible or visible signal (which does NOT move the print head).
	BS: Moves the print head one character position towards the left margin.
	HT: Moves the printer to the next horizontal tab stop.
		It remains unspecified how either party determines or establishes where such tab stops are located.
	LF: Moves the printer to the next print line, keeping the same horizontal position.
	VT: Moves the printer to the next vertical tab stop.
		It remains unspecified how either party determines or establishes where such tab stops are located.
	FF: Moves the printer to the top of the next page, keeping the same horizontal position.
	CR: Moves the printer to the left margin of the current line.

---
Telnet Command Definitions

Attributes:
	IAC: (Interpret As Command) Indicates the start of a Telnet command.
	NOP: No operation.
	DM: (Data Mark) The data stream portion of a Synch.
		This should always be accompanied by a TCP Urgent notification.
	BRK: NVT character Break.
	IP: The function Interrupt Process.
	AO: The function Abort Output
	AYT: The function Are You There.
	EC: The function Erase Character.
	EL: The function Erase Line
	GA: The Go Ahead signal.
	WILL: Indicates the desire to begin performing, or confirmation that you are now performing,
		the indicated option.
	WONT: Indicates the refusal to perform, or refusal to continue performing, the indicated option.
	DO: Indicates the request that the other party perform, or confirmation that you are
		expecting the other party to perform, the indicated option.
	DONT: Indicates the demand that the other party stop performing, or confirmation that you
		are no longer expecting the other party to perform, the indicated option.
	SB: Indicates what follows is a subnegotiation of the indicated option.
	SE: End of subnegotiation parameters.

---
Telnet Option Definitions

Attributes:
	ECHO: (User-to-Server) Asks the server to send Echos of the transmitted data.
	SGA: Suppress Go Ahead. Most modern servers should suppress it.
	TTYPE: Negotiate terminal type.
	NAWS: Negotiate About Window Size.
	LINEMODE: Allow line buffering to be negotiated.
	NEW_ENVIRON: Negotiate environment variables.
	CHARSET: Negotiate character set.

---
Mud Specific Options

Attributes:
	ATCP: Achaea Telnet Client Protocol.
	GMCP: Generic Mud Communication Protocol.
	MCCP1: Mud Client Compression Protocol V1.
	MCCP2: Mud Client Compression Protocol V2.
	MCCP3: Mud Client Compression Protocol V3.
	MSDP: Mud Server Data Protocol.
	MSP: Mud Sound Protocol.
	MSSP: Mud Server Status Protocol.
	MXP: Mud Extention Protocol.
	ZMP: Zenith Mud Protocol.
"""


# Future Modules:
from __future__ import annotations


# Protocol specifications.

# Achaea Telnet Client Protocol: http://www.ironrealms.com/rapture/manual/files/FeatATCP-txt.html
# End of Record: https://mudhalla.net/tintin/protocols/eor
# Generic Mud Communication Protocol: https://mudhalla.net/tintin/protocols/gmcp
# https://www.gammon.com.au/gmcp
# https://www.ironrealms.com/gmcp-doc
# Mud Client Compression Protocol: https://mudhalla.net/tintin/protocols/mccp
# http://www.gammon.com.au/mccp
# https://zuggsoft.com/zmud/mcp.htm
# https://smaugmuds.afkmods.com/mccp/protocol.html
# MUD Client Protocol: https://www.moo.mud.org/mcp
# Mud Master Chat Protocol: https://mudhalla.net/tintin/protocols/mmcp
# MUD NEW-ENVIRON Standard: https://mudhalla.net/tintin/protocols/mnes
# Mud Server Data Protocol: https://mudhalla.net/tintin/protocols/msdp
# Mud Server Link Protocol: https://mudhalla.net/tintin/protocols/mslp
# Mud Server Status Protocol: https://mudhalla.net/tintin/protocols/mssp
# MUD Sound Protocol: https://zuggsoft.com/zmud/msp.htm
# Mud Terminal Type Standard: https://mudhalla.net/tintin/protocols/mtts
# MUD eXtension Protocol: https://zuggsoft.com/zmud/mxp.htm
# Zenith MUD Protocol: http://discworld.starturtle.net/external/protocols/zmp.html


DESCRIPTIONS: dict[bytes, str] = {}


def describe(description: str, value: int) -> bytes:
	"""
	Stores the description of a negotiation.

	Args:
		description: The negotiation description.
		value: The ordinal value of the negotiation.

	Returns:
		The negotiation byte.
	"""
	byte: bytes = bytes([value])
	DESCRIPTIONS[byte] = description
	return byte


# ASCII characters.
NULL: bytes = bytes([0])
BEL: bytes = bytes([7])
BS: bytes = bytes([8])
HT: bytes = bytes([9])
LF: bytes = bytes([10])
VT: bytes = bytes([11])
FF: bytes = bytes([12])
CR: bytes = bytes([13])
CR_LF: bytes = CR + LF
CR_NULL: bytes = CR + NULL

# Telnet Commands.
XEOF: bytes = describe("XEOF", 236)  # End Of File.
SUSP: bytes = describe("SUSP", 237)  # Suspend Process.
ABORT: bytes = describe("ABORT", 238)  # Abort Process.
EOR: bytes = describe("EOR", 239)  # RFC 885.
SE: bytes = describe("SE", 240)  # End Subnegotiation.
NOP: bytes = describe("NOP", 241)  # No Operation.
DM: bytes = describe("DM", 242)  # Data Mark.
BRK: bytes = describe("BRK", 243)  # Break.
IP: bytes = describe("IP", 244)  # Interrupt Process permanently.
AO: bytes = describe("AO", 245)  # Abort output but let prog finish.
AYT: bytes = describe("AYT", 246)  # Are You There?
EC: bytes = describe("EC", 247)  # Erase Character.
EL: bytes = describe("EL", 248)  # Erase Line.
GA: bytes = describe("GA", 249)  # Go Ahead.
SB: bytes = describe("SB", 250)  # Begin Subnegotiation.
WILL: bytes = describe("WILL", 251)
WONT: bytes = describe("WONT", 252)
DO: bytes = describe("DO", 253)
DONT: bytes = describe("DONT", 254)
IAC: bytes = describe("IAC", 255)
IAC_IAC: bytes = IAC + IAC
COMMAND_BYTES: frozenset[bytes] = frozenset((XEOF, SUSP, ABORT, EOR, NOP, DM, BRK, IP, AO, AYT, EC, EL, GA))
COMMAND_ORDS: frozenset[int] = frozenset(ord(i) for i in COMMAND_BYTES)
NEGOTIATION_BYTES: frozenset[bytes] = frozenset((WILL, WONT, DO, DONT))
NEGOTIATION_ORDS: frozenset[int] = frozenset(ord(i) for i in NEGOTIATION_BYTES)

# Telnet Options.
# See https://www.iana.org/assignments/telnet-options
TRANSMIT_BINARY: bytes = describe("TRANSMIT_BINARY", 0)  # RFC 856.
ECHO: bytes = describe("ECHO", 1)  # RFC 857.
RECONNECT: bytes = describe("RECONNECT", 2)  # RFC 671.
SGA: bytes = describe("SGA", 3)  # RFC 858.
APPROX_MESSAGE_SIZE: bytes = describe("APPROX_MESSAGE_SIZE", 4)  # RFC unknown.
STATUS: bytes = describe("STATUS", 5)  # RFC 859.
TIMING_MARK: bytes = describe("TIMING_MARK", 6)  # RFC 860.
RCTE: bytes = describe("RCTE", 7)  # RFC 563, 581, 726.
OUTPUT_LINE_WIDTH: bytes = describe("OUTPUT_LINE_WIDTH", 8)  # RFC unknown.
OUTPUT_PAGE_SIZE: bytes = describe("OUTPUT_PAGE_SIZE", 9)  # RFC unknown.
NAOCRD: bytes = describe("NAOCRD", 10)  # RFC 652.
NAOHTS: bytes = describe("NAOHTS", 11)  # RFC 653.
NAOHTD: bytes = describe("NAOHTD", 12)  # RFC 654.
NAOFFD: bytes = describe("NAOFFD", 13)  # RFC 655.
NAOVTS: bytes = describe("NAOVTS", 14)  # RFC 656.
NAOVTD: bytes = describe("NAOVTD", 15)  # RFC 657.
NAOLFD: bytes = describe("NAOLFD", 16)  # RFC 658.
EXTENDED_ASCII: bytes = describe("EXTENDED_ASCII", 17)  # RFC 698.
LOGOUT: bytes = describe("LOGOUT", 18)  # RFC 727.
BM: bytes = describe("BM", 19)  # RFC 735.
DATA_ENTRY_TERMINAL: bytes = describe("DATA_ENTRY_TERMINAL", 20)  # RFC 732, 1043.
SUPDUP: bytes = describe("SUPDUP", 21)  # RFC 734, 736.
SUPDUP_OUTPUT: bytes = describe("SUPDUP_OUTPUT", 22)  # RFC 749.
SEND_LOCATION: bytes = describe("SEND_LOCATION", 23)  # RFC 779.
TTYPE: bytes = describe("TTYPE", 24)  # RFC 1091, MTTS.
END_OF_RECORD: bytes = describe("END_OF_RECORD", 25)  # RFC 885
TUID: bytes = describe("TUID", 26)  # RFC 927.
OUTMRK: bytes = describe("OUTMRK", 27)  # RFC 933.
TTYLOC: bytes = describe("TTYLOC", 28)  # RFC 946.
TELNET_3270_REGIME: bytes = describe("TELNET_3270_REGIME", 29)  # RFC 1041.
X3_PAD: bytes = describe("X3_PAD", 30)  # RFC 1053.
NAWS: bytes = describe("NAWS", 31)  # RFC 1073.
TERMINAL_SPEED: bytes = describe("TERMINAL_SPEED", 32)  # RFC 1079.
REMOTE_FLOW_CONTROL: bytes = describe("REMOTE_FLOW_CONTROL", 33)  # RFC 1372.
LINEMODE: bytes = describe("LINEMODE", 34)  # RFC 1116, 1184.
X_DISPLAY_LOCATION: bytes = describe("X_DISPLAY_LOCATION", 35)  # RFC 1096.
ENVIRON: bytes = describe("ENVIRON", 36)  # RFC 1408.
AUTHENTICATION: bytes = describe("AUTHENTICATION", 37)  # RFC 1416, 2941, 2942, 2943, 2951.
ENCRYPTION: bytes = describe("ENCRYPTION", 38)  # RFC 2946.
NEW_ENVIRON: bytes = describe("NEW_ENVIRON", 39)  # RFC 1571, 1572.
TN3270E: bytes = describe("TN3270E", 40)  # RFC 2355.
XAUTH: bytes = describe("XAUTH", 41)  # RFC unknown.
CHARSET: bytes = describe("CHARSET", 42)  # RFC 2066.
RSP: bytes = describe("RSP", 43)  # RFC unknown.
COM_PORT_CONTROL: bytes = describe("COM_PORT_CONTROL", 44)  # RFC 2217.
SUPPRESS_LOCAL_ECHO: bytes = describe("SUPPRESS_LOCAL_ECHO", 45)  # RFC unknown.
START_TLS: bytes = describe("START_TLS", 46)  # RFC unknown.
KERMIT: bytes = describe("KERMIT", 47)  # RFC 2840.
SEND_URL: bytes = describe("SEND_URL", 48)  # RFC unknown.
FORWARD_X: bytes = describe("FORWARD_X", 49)  # RFC unknown.
PRAGMA_LOGON: bytes = describe("PRAGMA_LOGON", 138)  # RFC unknown.
SSPI_LOGON: bytes = describe("SSPI_LOGON", 139)  # RFC unknown.
PRAGMA_HEARTBEAT: bytes = describe("PRAGMA_HEARTBEAT", 140)  # RFC unknown.
EXOPL: bytes = describe("EXOPL", 255)  # RFC 861.

# Mud Specific Options.
MSDP: bytes = describe("MSDP", 69)  # Mud Server Data Protocol.
MSSP: bytes = describe("MSSP", 70)  # Mud Server Status Protocol.
MCCP1: bytes = describe("MCCP1", 85)  # Mud Client Compression Protocol V1.
MCCP2: bytes = describe("MCCP2", 86)  # Mud Client Compression Protocol V2.
MCCP3: bytes = describe("MCCP3", 87)  # Mud Client Compression Protocol V3.
MSP: bytes = describe("MSP", 90)  # Mud Sound Protocol.
MXP: bytes = describe("MXP", 91)  # Mud Extention Protocol.
ZMP: bytes = describe("ZMP", 93)  # Zenith Mud Protocol.
ATCP: bytes = describe("ATCP", 200)  # Achaea Telnet Client Protocol.
GMCP: bytes = describe("GMCP", 201)  # Generic Mud Communication Protocol.

# Telnet LineMode Option (RFC 1184) Constants.
LINEMODE_MODE: bytes = bytes([1])
LINEMODE_EDIT: bytes = bytes([1])
LINEMODE_TRAPSIG: bytes = bytes([2])
LINEMODE_MODE_ACK: bytes = bytes([4])
LINEMODE_SOFT_TAB: bytes = bytes([8])
LINEMODE_LIT_ECHO: bytes = bytes([16])
LINEMODE_FORWARDMASK: bytes = bytes([2])
LINEMODE_SLC: bytes = bytes([3])
LINEMODE_SLC_SYNCH: bytes = bytes([1])
LINEMODE_SLC_BRK: bytes = bytes([2])
LINEMODE_SLC_IP: bytes = bytes([3])
LINEMODE_SLC_AO: bytes = bytes([4])
LINEMODE_SLC_AYT: bytes = bytes([5])
LINEMODE_SLC_EOR: bytes = bytes([6])
LINEMODE_SLC_ABORT: bytes = bytes([7])
LINEMODE_SLC_EOF: bytes = bytes([8])
LINEMODE_SLC_SUSP: bytes = bytes([9])
LINEMODE_SLC_EC: bytes = bytes([10])
LINEMODE_SLC_EL: bytes = bytes([11])
LINEMODE_SLC_EW: bytes = bytes([12])
LINEMODE_SLC_RP: bytes = bytes([13])
LINEMODE_SLC_LNEXT: bytes = bytes([14])
LINEMODE_SLC_XON: bytes = bytes([15])
LINEMODE_SLC_XOFF: bytes = bytes([16])
LINEMODE_SLC_FORW1: bytes = bytes([17])
LINEMODE_SLC_FORW2: bytes = bytes([18])
LINEMODE_SLC_MCL: bytes = bytes([19])
LINEMODE_SLC_MCR: bytes = bytes([20])
LINEMODE_SLC_MCWL: bytes = bytes([21])
LINEMODE_SLC_MCWR: bytes = bytes([22])
LINEMODE_SLC_MCBOL: bytes = bytes([23])
LINEMODE_SLC_MCEOL: bytes = bytes([24])
LINEMODE_SLC_INSRT: bytes = bytes([25])
LINEMODE_SLC_OVER: bytes = bytes([26])
LINEMODE_SLC_ECR: bytes = bytes([27])
LINEMODE_SLC_EWR: bytes = bytes([28])
LINEMODE_SLC_EBOL: bytes = bytes([29])
LINEMODE_SLC_EEOL: bytes = bytes([30])
LINEMODE_SLC_DEFAULT: bytes = bytes([3])
LINEMODE_SLC_VALUE: bytes = bytes([2])
LINEMODE_SLC_CANTCHANGE: bytes = bytes([1])
LINEMODE_SLC_NOSUPPORT: bytes = bytes([0])
LINEMODE_SLC_LEVELBITS: bytes = bytes([3])
LINEMODE_SLC_ACK: bytes = bytes([128])
LINEMODE_SLC_FLUSHIN: bytes = bytes([64])
LINEMODE_SLC_FLUSHOUT: bytes = bytes([32])
LINEMODE_EOF: bytes = bytes([236])
LINEMODE_SUSP: bytes = bytes([237])
LINEMODE_ABORT: bytes = bytes([238])

# Telnet Terminal Type (RFC 1091) Constants.
TTYPE_IS: bytes = bytes([0])
TTYPE_SEND: bytes = bytes([1])

# Telnet Environment Option (RFC 1572) Constants.
ENV_IS: bytes = bytes([0])
ENV_SEND: bytes = bytes([1])
ENV_INFO: bytes = bytes([2])
OLD_ENV_VAR: bytes = bytes([1])
OLD_ENV_VALUE: bytes = bytes([0])
ENV_VAR: bytes = bytes([0])
ENV_VALUE: bytes = bytes([1])
ENV_ESC: bytes = bytes([2])
ENV_USERVAR: bytes = bytes([3])

# Telnet Charset Option (RFC 2066) Constants.
CHARSET_REQUEST: bytes = bytes([1])
CHARSET_ACCEPTED: bytes = bytes([2])
CHARSET_REJECTED: bytes = bytes([3])
CHARSET_TTABLE_IS: bytes = bytes([4])
CHARSET_TTABLE_REJECTED: bytes = bytes([5])
CHARSET_TTABLE_ACK: bytes = bytes([6])
CHARSET_TTABLE_NAK: bytes = bytes([7])

# Mud Server Status Protocol Constants.
MSSP_VAR: bytes = bytes([1])
MSSP_VAL: bytes = bytes([2])

# Mud Server Data Constants.
MSDP_VAR: bytes = bytes([1])
MSDP_VAL: bytes = bytes([2])
MSDP_TABLE_OPEN: bytes = bytes([3])
MSDP_TABLE_CLOSE: bytes = bytes([4])
MSDP_ARRAY_OPEN: bytes = bytes([5])
MSDP_ARRAY_CLOSE: bytes = bytes([6])
