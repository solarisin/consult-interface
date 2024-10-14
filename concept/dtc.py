# dtc documentation
'''
11 Crank angle sensor/circuit (1988 to 1990); Crankshaft position sensor (1991 to 1996)
12 Air flow Meter/circuit open or shorted
13 Cylinder head temperature sensor(Maxima and 300ZX models); all others coolant temperature sensor circuit
14 Vehicle Speed Sensor signal circuit is open
15 Mixture ratio is too lean despite feedback control; fuel injector clogged
21 Ignition signal in the primary circuit is not being entered to the ECU during cranking or tuning
22 Fuel pump circuit (Maxima and 1987 and later 300ZX models); all others idle speed control valve or circuit
23 Idle switch (throttle valve switch) signal circuit open
24 Park/netural switch malfunctioning
25 Idle speed control valve circuit is open or shorted
26 Turbo boost
28 Cooling fan
29 Fuel system rich
31 1984 through 1986 EFI models; Problem in air conditioning system; all other models: ECU internal problem
32 1984 through 1986 EFI models; check starter system. All other models: EGR malfuntion (California models)
33 Oxygen sensor or circuit (300ZX left side) - all other models EGR malfunction
34 Detonation (Knock) sensor
35 Exhaust gas temperature sensor (California models)
36 EGR transducer
37 Closed loop control/front oxygen sensor (Maxima)
41 Maxima and 1984 through 1987 300ZX models; fuel temp sensor circuit. All other models: air temperature sensor circuit
42 1988 and later 300ZX models; fuel temperature sensor circuit; all other models: throttle sensor circuit
43 The mixture ratio is too lean despite feedback control; fuel injector clogged (1987 Sentra only): All others; Throttle position sensor circuit is open or shorted
44 No trouble codes stored in ECU
45 Injector fuel leak (California models only)
51 Fuel injector circuit open (California models only)
53 Oxygen sensor (300ZX right side)
54 Short between automatic transmission control unit(TCU) and ECU
55 Normal engine management system operation is indicated
63 Misfire detected - cylinder no. 6
64 Misfire detected - cylinder no. 5
65 Misfire detected - cylinder no. 4
66 Misfire detected - cylinder no. 3
67 Misfire detected - cylinder no. 2
68 Misfire detected - cylinder no. 1
71 Misfire detected - random
72 Catalytic converter malfunction (right side)
74 EVAP pressure sensor
75 EVAP leak
76 Fuel injection system
77 Rear oxygen sensor
81 Vacuum cut bypass valve
82 Crankshaft sensor
84 Automatic trans-to-fuel injection communication
85 VTC solenoid
87 EVAP canister purge control
91 Front oxygen sensor
95 Crankshaft sensor
98 Coolant temperature sensor
101 Camshaft sensor
103 Park/neutral switch
105 EGR and canister control valve
108 EVAP volume control
0505 No self diagnostic codes present
0101 Camshaft position sensor
0102 Mass airflow sensor/circuit
0103 Coolant temperature sensor
0104 Vehicle speed sensor
0111

EVAP purge flow monitoring system
0114 Fuel system rich
0115 Fuel system lean
0201 Ignition signal
0203 Closed throttle switch
0205 IACV/AAC valve
0208 Overheating
0213 EVAP system
0214 Purge volume control valve
0301 ECM control unit
0302 EGR function
0303

Front heated oxygen sensor malfunction
0304 Knock sensor
0305 Exhaust gas temperature sensor
0306 EGRC BPT valve
0307 Closed loop operation
0309 Vent control valve
0311 Vacuum cut valve bypass valve
0312 EVAP system purge control valve
0401 Intake air temperature sensor
0402 Fuel temperature sensor or circuit
0403 Throttle position sensor
0409 Front oxygen sensor
0410 Front oxygen sensor
0411 Front oxygen sensor
0412 Front oxygen sensor
0503 Front oxygen sensor
0510 Rear oxygen sensor
0511 Rear oxygen sensor
0512 Rear oxygen sensor
0514 EGR system
0605 Cylinder 4 misfire
0606 Cylinder 3 misfire
0607 Cylinder 2 misfire
0608 Cylinder 1 misfire
0701 Multiple cylinder misfire
0702 Catalytic converter
0704 EVAP system
0705 EVAP system
0706 Fuel injection system malfunction
0707 Rear oxygen sensor
0801 Vacuum cut valve bypass valve or circuit
0802 Crankshaft sensor
0803 Absolute pressure sensor
0804 A/T diagnosis comm line
0807 EVAP canister purge control
0901 Front oxygen sensor heater
0902 Rear oxygen sensor heater
0903 Vent control valve
0905 Crankshaft position sensor
0908 Coolant temperature sensor
1003 Park/neutral switch
1005 EGR solenoid valve circuit
1008 EVAP system
1101 Inhibitor switch
1102 A/T vehicle speed sensor
1103 A/T first signal
1104 A/T second signal
1105 A/T third signal
1106 A/T fourth signal
1107 A/T torque converter clutch
1108 Shift solenoid A
1201 Shift solenoid B
1203 Overrun clutch solenoid
1204 TCC solenoid
1205 Line pressure solenoid
1206 TPS for A/T
1207 Speed signal A/T
1208 A/T fluid temperature sensor
1302 MAP/BAR switch solenoid valve or circuit
1305 Fuel pump control module or circuit
1308 Cooling fan 
'''
'''
11
Camshaft position sensor circuit
- Either 1 degree or 180 degrees signal is not detected by the EDM for the first few seconds during the engine cranking- Either 1 degree or 180 degrees signal is not detected by the ECM often enough while the engine speed is higher than the specified rpm
- The relation between 1 degree and 180 degree signals is not in the normal range during the specified rpm
- Harness or connectors (The sensor circuit is open or shorted.)
- Camshaft position sensor
- Starer motor
- Starting system circuit (EL selection)- Dead (Weak) battery

12
Mass air flow sensor circuit
- An excessively high or low voltage is entered to ECM
- Voltage sent to ECM is not practical when compared with the camshaft position sensor signal and throttle position sensor signals.
- Harness or connectors (The sensor circuit is opened or shorted.)
- Mass air flow sensor

13
Engine coolant temperature sensor circuit
- An excessively high or low voltage from the sensor is detected by the ECM
- Harness or connectors (The sensor circuit is opened or shorted.)
- Engine coolant temperature sensor

14
Vehicle speed sensor circuit
- The almost 0 MPH signal from the sensor is detected by the ECM even when vehicle is driving
-Harness or connectors (The sensor circuit is open or shorted.)
- Vehicle speed sensor

21
Ignition signal circuit
-The ignition signal in the primary circuit is not detected by the ECM during engine cranking or running.
-Harness or connectors (The ignition primary circuit is open or shorted.)
- Power transistor unit- Camshaft position sensor
- Camshaft position sensor circuit

25
Idle speed control function
-The idle speed control function does not operate properly.
- Harness or connectors (The valve circuit it shorted.)
- IACV
-AAC valve
- Harness or connectors (The valve circuit is open.)

28
Cooling fan circuit
- Cooling fan does not operate properly. (Overheat)
- Cooling system does not operate properly. (Overheat)
- Engine coolant was not added to the system using the proper filling method.
- Harness or connectors. (The cooling fan circuit is open or shorted.)
- Cooling fan
- Radiator hose
- Radiator
- Radiator cap
- Water pump
- Thermostat

31
ECM
- ECM calculation function is malfunctioning
- ECM (ECCS control module)

32
- EGR function
- The EGR flow is excessively low or high during the specified driveing condition.
- EGR valve stuck closed, open, or leaking- Passage obstructed
- EGR and canister control solenoid valve
- Tube leaking for EGR valve vacuum
- EGRC-BPT valve leaking

33
Front ocygen sensor circuit
- An excessively high voltage from the sensor is detected by the ECM
- The voltage from the sensor is constantly approx. 0.3V.
- The specified maximum and minimum voltages from the sensor are not reached.
- It takes more than the specified time for the sensor to respond between rich and lean.
- Harness or connectors (The sensor circuit is open or shorted.)
- Front oxygen sensor- Injectors
- Intake air leaks- Fuel pressure

34
Knock sensor circuit
- An excessively low or high voltage from the sensor is detected by the ECM.
- Harness or connectors (The sensor circuit is open or shorted.)
- Knock Sensor

35
EGR temperature sensor circuit
- An excessively low or high voltage from the sensor is defected by the ECM, evn when engine coolant temperature is low or high.
- Harness or connectors (The sensor circuit is open or shorted.)
- EGR temperature sensor

36
EGRC-BPT valve function
- EGRC-BPT valve does not operate properly
- EGRC-BPT valve- Rubber tube (obstructed or misconnected)

37
Closed loop control
- The closed loop control function does not operate even when vehicle is driving in the specified condition.
- The front oxygen sensor circuit is open or shorted.- Front oxygen sensor

41
Intake air temperature sensor circuit
- An excessively low or high voltage from the sensor is detected by the ECM.
- Voltage sent to ECM is not practical when compared with the engine coolant temerature sensor signal.
- Harness or connectors (The sensor circuit is open or shorted)
- Intake air temperature sensor

43
Throttle position sensor circuit
- An excessively low or high voltage from the sensor is detected by the ECM.
- Voltage sent to ECM is not practical when compared with the mass air flow sensor and camshaft position sensor signals.
- Harness or connectors (The sensor circuit is open or shorted.)
- Throttle position sensor

55
No failure
- No malfunction related to OBD system is detected by either ECM or A/T control unit.
- No failure

65
No. 4 cylinder misfire
- (Three-way catalyst damage) The misfire occurs, which will damage three way catalyst by overheating.
- (Exhaust quality deterioration) The misfire occurs, which will not damage three way catalyst but will affect emission deterioration.
- Improper spark plug
- The ignition secondary circuit is open or shorted.
- Insufficient compression
- Incorrect fuel pressure
- EGR valve
- The injector circuit is open or shorted.
- Injectors
- Lack of fuel
- Magnetized flywheel (drive plate)

66
No. 3 cylinder misfire
see above
see above

67
No. 2 cylinder misfire
see above
see above

68
No. 1 cylinder misfire
see above
see above

71
Multiple cylinder misfire
see above
see above

72
Three way catalyst function
- Three way catalyst does not operate properly.
- Three way catalyst does not have enogh oxygen storage capacity.
- Three way catalyst
- Exhaust tube
- Intake air leak
- Injectors- Injector Leak

76
Fuel injection system function
- Fuel injection system does not operate properly.
- The amount of mixture ratio compensation is excessive (The mixture ratio is too lean or too rich.)
- Intake air leak
- Front oxygen sensor
- Injectors
- Exhaust gas leak
- Incorrect fuel pressure
- Mass air flor sensor
- Lack of fuel

77
Rear heated oxygen sensor circuit
- An excessively high voltage from the sensor is detected by the ECM.
- The specified maximum and minimum voltages from the sensor are not reached.
- It takes more than the specified time for the sensor to respond between rich and lean
- Harness or connectors (The sensor circuit is open or shorted.)
- Rear heated oxygen sensor
- Fuel pressure
- Injectors
- Intake air leaks

82
Crankshaft position sensor (OBD) circuit
- The proper pulse signal from the sensor is not detected by the ECM while the engine is running at the specified rpm.
- Harness or connectors (The sensor circuit is open or shorted.)
- Rear heated oxygen sensor
- Fuel pressure
- Injectors
- Intake air leaks

84
A/T diagnosis communication line
- An incorrect signal from A/T control unit is detected by the ECM.
- Harness or connectors (The communication line circuit is open or shorted.
- Dead (Weak) battery
- A/T control unit

95
Crankshaft position sensor (OBD)
- The chipping of the flywheel or drive plate gear tooth is detected by the ECM
- Harness or connectors
- Crankshaft position sensor (OBD)
- Flywheel

98
Engine coolant temperature sensor function
- Voltage sent to ECM from the sensor is not practical, even when some time has passed after starting the engine
- Engine coolant temperature is insufficient for closed loop fuel control
- Harness or connectors (The swith circuit is open or shorted)
- Neutral position switch
- Inhibitor switch

103
Park/Neutral position switch circuit
- The signal of the park/neutral position switch is not changed in the process of engine starting and driving.
- Harness or connectors (The valve circuit is open or shorted)
- EGR and canister control solenoid valve

-
Signal circuit from A/T control unit to ECM
- ECM recieves incorrect voltage from A/T control unit continuously
- Harness or connectors (The circuit between ECM and A/T control unit is open or shorted)

111
Inhibitor switch circuit
-A/T control unit does not recieve the correct voltage signal from the switch based on the gear position.
- Harness or connectors (The switch circuit is open or shorted)
- Inhibitor switch

112
Revolution sensor
- A/T control unit does not recieve the proper voltage signal from the sensor
- Harness or connectors (The switch circuit is open or shorted)
- Revolution sensor

113
Improper shifting to 1st gear position
- A/T can not be shifted to the 1st gear position even electrical circuit is good
- Shift solenoid valve A
- Shift solenoid valve B
- Overrun clutch solenoid valve
- Line pressure solenoid valve
- Each clutch
- Hydraulic control circuit

114
Improper shifting to 2nd gear position
- A/T can not be shifted to the 2nd gear position even electrical circuit is good
see above

115
Improper shifting to 3rd gear position
- A/T can not be shifted to the 3rd gear position even electrical circuit is good
see above

116
Improper shifting to 4th gear position or TCC
- A/T can not be shifted to the 4th gear position or perform lock-up even electrical circuit is good
T/C clutch solenoid valve

118
Shift solenoid valve A
- A/T control unit detects the improprt voltage drop when it tries to operate the solenoid valve
- Harness or connectors (The switch circuit is open or shorted)

121
Shift solenoid valve B
- A/T control unit detects the improprt voltage drop when it tries to operate the solenoid valve
- Harness or connectors (The switch circuit is open or shorted)
- Shift solenoid valve A

123
Overrun clutch solenoid valve
- A/T control unit detects the improprt voltage drop when it tries to operate the solenoid valve
- Harness or connectors (The switch circuit is open or shorted)
- Shift solenoid valve B
- Overrun clutch solenoid valve

124
T/C clutch solenoid valve
- A/T control unit detects the improprt voltage drop when it tries to operate the solenoid valve
- Harness or connectors (The switch circuit is open or shorted)
- T/C clutch solenoid valve

125
Line pressure solenoid valve
- A/T control unit detects the improprt voltage drop when it tries to operate the solenoid valve
- Harness or connectors (The switch circuit is open or shorted)
- Line pressure solenoid valve

126
Throttle position sensor
- A/T control unit recieves an excessively low or high voltage signal from the sensor
- Harness or connectors (The switch circuit is open or shorted)
- Throttle position sensor

127
Engine speed signal
- A/T control unit does not recieve the proper voltage signal from the ECM
- Harness or connectors (The switch circuit is open or shorted)

128
Fluid temperature sensor
- A/T control unit recieves an excessively low or high voltage signal from the sensor
- Harness or connectors (The switch circuit is open or shorted)
- Fluid temperature sensor
'''


class DTC():
    # TODO
    # - determine how 3-digit codes work
    # - add retrieval of possible causes in addition to the name
    code_map = {
        11: "Camshaft Position Sensor",
        12: "Air Flow Meter",
        13: "Coolant Temperature Sensor",
        14: "Vehicle Speed Sensor",
        21: "Ignition Signal",
        25: "IACV - AAC Valve",
        26: "Boost Pressure Sensor",
        31: "ECM Fault",
        32: "Exhaust Gas Recirculation System",
        33: "Front EGO Sensor (O2-1 Sensor)",
        34: "Knock Sensor",
        35: "EGR Temperature Sensor",
        36: "EGR BPT Valve",
        37: "Closed Loop System",
        41: "Intake Air Temperature Sensor",
        43: "Throttle Position Sensor",
        54: "Signal from Auto Transmission",
        55: "Other Malfunction. CONSULT Terminal Required",
        63: "Cylinder 6 Misfire (?)",
        64: "Cylinder 5 Misfire (?)",
        65: "Cylinder 4 Misfire",
        66: "Cylinder 3 Misfire",
        67: "Cylinder 2 Misfire",
        68: "Cylinder 1 Misfire",
        71: "Random Misfire",
        72: "TW Catalyst System",
        76: "Fuel Injection System",
        77: "Rear EGO Sensor (O2-2)",
        82: "Crank Position Sensor",
        84: "Automatic Transmission Diagnostic Comms Line",
        95: "Crank Position Cog",
        98: "Coolant Temperature Sensor"
    }

    def __init__(self, code, starts):
        self.code = code
        self.starts = starts
    
    def name(self):
        if self.code in self.code_map:
            return self.code_map[self.code]
        else:
            return "Unknown code"