import datetime
import math
import socket
import sys

import minimalmodbus
import serial


class ThermalChamber:
    def read_temp(self) -> float:
        raise NotImplementedError

    def read_humidity(self) -> float:
        """
        Reads the current humidity
        """
        raise NotImplementedError

    def read_current_loop_num(self) -> int:
        """
        Read the number of loop jumps performed so far in this profile.
        """
        raise NotImplementedError

    def read_interval(self) -> int:
        """
        Read the current step/interval within the current profile.
        """
        raise NotImplementedError

    def read_interval_time_left(self) -> datetime.timedelta:
        """
        Read the time remaining in the current interval/step.
        """
        raise NotImplementedError

    def stop_profile(self):
        """
        Terminate the currently running profile.
        """
        raise NotImplementedError

    def close(self):
        """
        Close the interface to the thermal chamber.
        """
        raise NotImplementedError


def with_retries(max_retries, exceptions=(minimalmodbus.NoResponseError, minimalmodbus.InvalidResponseError)):
    def decorator(func):
        def inner(*args, **kwargs):
            retry = max_retries
            err = None
            while retry > 0:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retry -= 1
                    err = e
            if err is not None:
                raise err
        return inner
    return decorator


class BigBlue(ThermalChamber):
    """
    Hacked-up class to communicate with "Big Blue" Thermotron via Modbus.
    GSK note: some of this code is probably over-complicated, e.g. the
              two's complement conversions, but I've mostly just pasted in
              stuff that was working without trying to improve readability.
              Fixing this is a TODO
    """

    def __init__(self, port, close_port_after_each_call: bool = False):
        self.interface = minimalmodbus.Instrument(
            port=port,
            slaveaddress=2,
            close_port_after_each_call=close_port_after_each_call
        )
        self.interface.serial.SERIAL_TIMEOUT = 3
        self.interface.debug = False

        # set temperature units to Celsius if not already
        self.interface.write_register(901, 1)

    def close(self):
        self.interface.serial.close()

    @with_retries(max_retries=10)
    def read_register(self, *args, **kwargs):
        return self.interface.read_register(*args, **kwargs)

    @with_retries(max_retries=10)
    def read_registers(self, *args, **kwargs):
        return self.interface.read_registers(*args, **kwargs)

    @with_retries(max_retries=10)
    def write_register(self, *args, **kwargs):
        return self.interface.write_register(*args, **kwargs)

    @with_retries(max_retries=10)
    def write_registers(self, *args, **kwargs):
        return self.interface.write_registers(*args, **kwargs)

    def read_temp(self) -> float:
        """
        Reads current temperature
        """
        temp = self.read_register(100)
        b = temp.to_bytes(2, byteorder=sys.byteorder, signed=False)
        temp = int.from_bytes(b, byteorder=sys.byteorder, signed=True) / 10
        return temp

    def read_temp_setpoint(self) -> float:
        """
        Reads temperature setpoint
        """
        temp_setpoint = self.read_register(300)
        b = temp_setpoint.to_bytes(2, byteorder=sys.byteorder, signed=False)
        temp_setpoint = int.from_bytes(b, byteorder=sys.byteorder, signed=True) / 10
        return temp_setpoint

    def set_temp(self, temp: int):
        """
        Updates the temperature setpoint
        """
        if temp >= 0:
            self.write_register(300, temp, 1)
        else:
            temp = temp * -10
            # convert to two's complement binary in a goofy way
            binstr = ("{0:016b}".format(temp))
            binstr = binstr.replace('0', '2')
            binstr = binstr.replace('1', '0')
            binstr = binstr.replace('2', '1')
            temp = int(binstr, base=2) + 1
            self.write_register(300, temp, 0)

    def set_humidity(self, hum: int):
        """
        Updates the humidity setpoint
        """
        self.write_register(319, hum, 0)

    def read_humidity(self) -> float:
        """
        Reads the current humidity
        """
        return float(self.read_register(104))

    def read_humidity_setpoint(self) -> float:
        """
        Reads the humidity setpoint...in case you couldn't guess that
        """
        return float(self.read_register(319))

    def temp_on(self):
        """
        Turns on the temperature channel
        """
        self.write_register(2000, 1, 0)

    def temp_off(self):
        """
        Turns off the temperature channel
        """
        self.write_register(2000, 0, 0)

    def humidity_on(self):
        """
        Turns on the humidity channel
        """
        self.write_register(2010, 1, 0)

    def humidity_off(self):
        """
        Turns off the humidity channel
        """
        self.write_register(2010, 0, 0)

    def read_current_loop_num(self):
        """
        Read the number of loop jumps performed so far in this profile.
        This is labeled "Jump Count, current profile status" in manual
        """
        return self.read_register(4126)

    def read_interval(self):
        """
        Read the current step/interval within the current profile.
        This is labeled "Step Number, current profile" in manual
        """
        return self.read_register(4101)

    def read_intervals_remaining(self) -> int:
        """
        Read the number of steps/intervals remaining in the profile.
        This doesn't include any repetitions produced by jump steps.
        """
        return self.read_register(1219, 0)

    def read_interval_time_left(self) -> datetime.timedelta:
        """
        Read the time remaining in the current interval/step.
        These registers are labeled "Hours/minutes/seconds remaining" in the manual
        """
        hours, minutes, seconds = self.read_registers(4119, 3)
        return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)

    def hold_profile(self) -> int:
        """
        Simulates a "profile hold" keypress on the Watlow F4 controller.
        :return:
        """
        return self.write_register(1210, 1)

    def stop_profile(self) -> int:
        """
        Terminates the currently running profile.
        :return:
        """
        return self.write_register(1217, 1)


class BigGray(ThermalChamber):
    """
    Hacked-up class to communicate with "Big Gray" Thermotron via Ethernet.
    GSK note: I've mostly just pasted in stuff that was working without trying
              to improve readability.
              TODO: clean up code
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def close(self):
        pass

    def read_temp(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall(b'PVAR1?\n')
            return float(s.recv(256))

    def read_humidity(self) -> float:
        """
        Reads the current humidity
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall(b'PVAR2?\n')
            return float(s.recv(256))

    def read_current_loop_num(self) -> int:
        """
        Read the number of loop jumps performed so far in this profile.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            # first get number of loops total
            s.sendall(b'NUML?\n')
            num_loops = int(s.recv(256))
            # then get number of loops remaining
            s.sendall(b'LLFT?\n')
            loops_left = int(s.recv(256))
            return num_loops - loops_left

    def read_interval(self) -> int:
        """
        Read the current step/interval within the current profile.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall(b'INTN?\n')
            return int(s.recv(256))

    def read_interval_time_left(self) -> datetime.timedelta:
        """
        Read the time remaining in the current interval/step.
        These registers are labeled "Hours/minutes/seconds remaining" in the manual
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall(b'TLFT?\n')
            time_left_str = s.recv(1024).decode('utf-8')
            hh, mm, ss = tuple([int(s) for s in time_left_str.strip().split(':')])
            return datetime.timedelta(
                hours=hh,
                minutes=mm,
                seconds=ss
            )

    def hold_profile(self) -> str:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall(b'HOLD\n')
            return s.recv(256).decode('utf-8')

    def stop_profile(self) -> str:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall(b'STOP\n')
            return s.recv(256).decode('utf-8')


class ESPEC(ThermalChamber):
    """
     Hacked-up class to communicate with ESPEC thermal chambers via (virtual) serial port.
     FIXME: this has not been tested on any hardware as of 05 Dec 2022.
     FIXME: this was named in a way that made sense at the time, but there will probably be ESPEC thermal chambers that
        do not work with the communications specified here.
    """
    def __init__(self, port):
        self.interface = serial.serial_for_url(url=port)

    def close(self):
        self.interface.close()

    def _monitor_chamber_conditions(self) -> dict:
        # TODO: this could almost certainly be rewritten in a more maintainable way so we don't have to keep track of
        #   indices in each result list. Consider this if we need to modify this code in future
        self.interface.reset_input_buffer()
        self.interface.write(b'MON?\n')
        self.interface.flush()
        # TODO: see if delay is needed here
        result = self.interface.readline()

        chamber_conditions = {
            'temp': math.nan,
            'humidity': math.nan,
            'operating_mode': 'UNKNOWN',
            'num_alarms': -1,
        }
        try:
            result = [s.strip() for s in result.split(',')]
            if len(result) == 4:
                # humidity is included
                chamber_conditions.update(
                    temp=float(result[0]),
                    humidity=float(result[1]),
                    operating_mode=result[2],
                    num_alarms=int(result[3])
                )
            elif len(result) == 3:
                # humidity is not included; temp-only chamber
                chamber_conditions.update(
                    temp=float(result[0]),
                    operating_mode=result[1],
                    num_alarms=int(result[2])
                )
            # otherwise response was invalid and cannot be parsed; throw it out
        except ValueError as e:
            # TODO: use logging instead of print
            print(e)
        return chamber_conditions

    def _monitor_program_status(self) -> dict:
        # TODO: this could almost certainly be rewritten in a more maintainable way so we don't have to keep track of
        #   indices in each result list or duplicate formatting. Consider this if we need to modify this code in future

        program_status = {
            'current_step_num': -1,
            'target_temp': math.nan,
            'target_humidity': math.nan,
            'time_remaining': datetime.timedelta(days=-1),
            'repeats_remaining_a': -1,
            'repeats_remaining_b': -1
        }

        self.interface.reset_input_buffer()
        self.interface.write(b'PRGM MON?\n')
        self.interface.flush()
        # TODO: see if delay is needed here
        results = self.interface.readline()

        try:
            results = [s.strip() for s in results.split(',')]
            if len(results) == 6:
                # humidity is included
                program_status.update(
                    current_step_num=int(results[0]),
                    target_temp=float(results[1]),
                    target_humidity=float(results[2]),
                    time_remaining=datetime.datetime.strptime(results[3], '%H:%M') - datetime.datetime(1900, 1, 1),
                    repeats_remaining_a=int(results[4]),
                    repeats_remaining_b=int(results[5]),
                )
            elif len(results) == 5:
                # humidity is not included; temp-only chamber
                program_status.update(
                    current_step_num=int(results[0]),
                    target_temp=float(results[1]),
                    time_remaining=datetime.datetime.strptime(results[2], '%H:%M') - datetime.datetime(1900, 1, 1),
                    repeats_remaining_a=int(results[3]),
                    repeats_remaining_b=int(results[4]),
                )
            # otherwise response was invalid and cannot be parsed; throw it out
        except ValueError as e:
            # TODO: use logging instead of print
            print(e)
        return program_status

    def read_temp(self) -> float:
        return self._monitor_chamber_conditions()['temp']

    def read_humidity(self) -> float:
        return self._monitor_chamber_conditions()['humidity']

    def read_interval(self) -> int:
        return self._monitor_program_status()['current_step_num']

    def read_current_loop_num(self) -> int:
        # TODO: should this be repeats_remaining_a or repeats_remaining_b?
        return self._monitor_program_status()['repeats_remaining_a']

    def read_interval_time_left(self) -> datetime.timedelta:
        return self._monitor_program_status()['time_remaining']

    def stop_profile(self):
        self.interface.reset_input_buffer()
        self.interface.write(b'POWER, OFF\n')
        self.interface.flush()
