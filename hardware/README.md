# Reconfigurable Digital Integrated Circuit Test Fixture - Hardware

The hardware encompasses circuit simulations, schematics, chassis and any other physical component of the **Reconfigurable Digital Integerated Circuit Test Fixture**.

## Some altium/circuit stuff

## Chassis

All files included are of the SolidWorks CAD of the IC test fixture chassis design.

This includes raw pre-fab chassis consisting of a top, front, rear, and bottom chassis, modified chassis with cutouts for the PCB on the top, front, and bottom chassis, and the CAD files for hardware used to fully assemble the IC test fixture, including screws, standoffs, and rubber feet.

Drawings are present showing each chassis parts individually, along with their measurements and cutouts. The Chassis is made of ABS plastic.

The pre-fabricated chassis is a JB-65 Desktop Electronics Enclosure, by Polycase and can be orderd from https://www.polycase.com/jb-65

Physical assembly of the chassis can be done with the chassis screws provided with the chassis by Polycase, 8x #4-40 Pan screws, 4x #4-40 1" hex standoffs, and 4x 0.5" cylindrical bumper rubber feet along with the IC test fixture PCB.

## Spice Simulations

Voltage reference (VREF) circuits consist of a TLV431 shunt regulator component with a $1.24\ V$ reference voltage, a voltage divider resistor circuit to set the VREF voltage, and a current limiting resistor to restrict the amount of current that can flow through the circuit.

For all VREF circuits within the IC test fixture, $V_{in} = 5\ V$, $V_{ref} = 1.24\ V$.

The formula for all the VREF circuits is:

$$V_{out} = V_{ref} \left(1 + \frac{R_1}{R_2}\right)$$

where $R_2 = 2490\ \Omega$ for consistency.

$V_{out}$ is set to $1.8\ V$, $2.5\ V$, $3.3\ V$, $4.0\ V$, or $4.5\ V$ for the VREF circuit, which is used to find each circuit's $R_1$ value, which is then chosen from the closest available 0.1% tolerance value.

The current limiting resistor ($R_3$) is equal to: 
$$R_3 = \frac{\left(V_{in} - V_{out}\right)}{\left(I_{out} + I_{cathode}\right)}$$

## Documentation

TODO

## License

The hardware portion of the **Reconfigurable Digital Integrated Circuit Test Fixture** is under a CERN-OHL-P-2.0 license.
