
class BigBlue():
    """
    Hacked-up class to communicate with "Big Blue" Thermotron via Modbus.
    GSK note: some of this code is probably over-complicated, e.g. the
              two's complement conversions, but I've mostly just pasted in
              stuff that was working without trying to improve readability.
              Fixing this is a TODO
    """

    def __init__(self):
        self.temp = 20.1
        self.temp_setpoint = 25.0
        self.humidity = 30.5
        self.humidity_setpoint = 35.0

    def read_temp(self) -> float:
        """
        Reads current temperature
        """
        return self.temp

    def read_temp_setpoint(self) -> float:
        """
        Reads temperature setpoint
        """
        return self.temp_setpoint

    def read_humidity(self) -> float:
        """
        Reads the current humidity
        """
        return self.humidity

    def read_humidity_setpoint(self) -> float:
        """
        Reads the humidity setpoint...in case you couldn't guess that
        """
        return self.humidity_setpoint
