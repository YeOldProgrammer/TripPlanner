import os
import sys
import os
import json
import shutil
import datetime

FIELD_IDX = 'Idx'
FIELD_DAY = 'Day'
FIELD_EVENT_IDX = 'Evt'
FIELD_DATE = 'Date'
FIELD_TYPE = 'Type'
FIELD_WHERE = 'Where'
FIELD_DESCRIPTION = 'Description'
FIELD_NOTES = 'Notes'
FIELD_TIME = 'Time'
FIELD_FIXED = 'Fix'
FIELD_START = 'Start'
FIELD_STOP = 'Stop'
FIELD_START_DT = 'Start_DT'
FIELD_STOP_DT = 'Stop_DT'
FIELD_LIST = [FIELD_DAY, FIELD_EVENT_IDX, FIELD_DATE, FIELD_TYPE, FIELD_WHERE, FIELD_DESCRIPTION,
              FIELD_NOTES, FIELD_TIME, FIELD_FIXED, FIELD_START, FIELD_STOP]
IGNORE_FIELD_LIST = [FIELD_IDX]

FIELD_TYPE_VISIT = 'Visit'
FIELD_TYPE_MEAL = 'Meal'
FIELD_TYPE_DRIVE = 'Drive'
FIELD_TYPE_FREE = 'Free'
FIELD_TYPE_STAY = 'Stay'
FIELD_TYPE_OTHER = 'Other'
FIELD_TYPE_TODO = 'TODO'
VALID_FIELD_TYPES = [FIELD_TYPE_VISIT, FIELD_TYPE_DRIVE, FIELD_TYPE_FREE, FIELD_TYPE_STAY, FIELD_TYPE_OTHER,
                     FIELD_TYPE_MEAL, FIELD_TYPE_TODO]


class Trip:
    def __init__(self, file_name):
        print("Loading File: %s" % os.path.relpath(file_name))
        if os.path.exists(file_name) is False:
            raise FileNotFoundError("Trip file is not valid '%s'" % file_name)

        self.file_name = ''
        self.first_date = datetime.datetime.today()
        self.events = []
        self.days = {}

        self.file_name = file_name

        with open(file_name) as trip_fh:
            trip_headers = []
            for header_idx, trip_header in enumerate(trip_fh.readline().split('|')[1:-1]):
                trip_header = trip_header.strip()
                if trip_header not in FIELD_LIST and trip_header not in IGNORE_FIELD_LIST:
                    raise ValueError("Unknown field '%s'" % trip_header)
                trip_headers.append(trip_header.strip())

            line_id = 1
            line_idx = -1
            for trip_line in trip_fh.readlines():
                line_id += 1
                event_dict = {}

                if trip_line.startswith('|-'):
                    continue

                if trip_line.strip() == '':
                    break

                trip_fields = trip_line.split('|')[1:-1]
                for header_idx, trip_field in enumerate(trip_fields):
                    try:
                        header = trip_headers[header_idx]
                    except Exception as error_text:
                        print("Line:%d is not valid:%s" % (line_id, trip_line))
                        sys.exit(1)

                    event_dict[header] = trip_field.strip()
                for header in FIELD_LIST:
                    if header not in event_dict:
                        event_dict[header] = ''

                if len(self.events) == 0:
                    try:
                        self.first_date = datetime.datetime.strptime(event_dict[FIELD_DATE], "%m/%d/%y, %a")
                    except Exception as error_text:
                        print("Error Text 1:%s" % error_text)
                        try:
                            self.first_date = datetime.datetime.strptime(event_dict[FIELD_DATE], "%m/%d/%y")
                        except Exception as error_text:
                            print("Error Text 2:%s" % error_text)
                            self.first_date = datetime.datetime.today()
                    event_dict[FIELD_DATE] = self.first_date
                else:
                    event_dict[FIELD_DATE] = self.first_date + datetime.timedelta(days=int(event_dict[FIELD_DAY]))

                line_idx += 1
                event_dict[FIELD_IDX] = line_idx

                self.events.append(TripEvent(line_id, event_dict))

        self.analyze_trip()

    def analyze_trip(self):
        total = {'Total': 0}
        for event_type in VALID_FIELD_TYPES:
            total[event_type] = 0

        day_event_idx = 1
        for event_idx in range(len(self.events)):
            event = self.events[event_idx]

            if event.data[FIELD_START] != '':
                event.data[FIELD_STOP] = event.data[FIELD_START] + datetime.timedelta(hours=event.data[FIELD_TIME])

            if event.data[FIELD_DAY] not in self.days:
                self.days[event.data[FIELD_DAY]] = {}
                for event_type in VALID_FIELD_TYPES:
                    self.days[event.data[FIELD_DAY]][event_type] = 0
                self.days[event.data[FIELD_DAY]]['Total'] = 0
                self.days[event.data[FIELD_DAY]]['Start'] = ''
                self.days[event.data[FIELD_DAY]]['Stop'] = ''
                self.days[event.data[FIELD_DAY]]['First_Event'] = event_idx
                self.days[event.data[FIELD_DAY]]['Last_Event'] = event_idx
                self.days[event.data[FIELD_DAY]]['Meals'] = 0
                day_event_idx = 1
            else:
                day_event_idx += 1

            event.data[FIELD_EVENT_IDX] = day_event_idx

            self.days[event.data[FIELD_DAY]][event.data[FIELD_TYPE]] += event.data[FIELD_TIME]
            self.days[event.data[FIELD_DAY]]['Total'] += event.data[FIELD_TIME]
            self.days[event.data[FIELD_DAY]]['Last_Event'] = event_idx

            if event.data[FIELD_TYPE] == FIELD_TYPE_MEAL:
                self.days[event.data[FIELD_DAY]]['Meals'] += 1

            for key in ['Start', 'Stop']:
                if isinstance(event.data[key], str) and event.data[key] == '':
                    event.data[key + '_DT'] = event.data[key]
                    continue

                if key == 'Start' and (self.days[event.data[FIELD_DAY]][key] == '' or
                        self.days[event.data[FIELD_DAY]][key] > event.data[key]):
                    self.days[event.data[FIELD_DAY]][key] = event.data[key]
                elif key == 'Stop' and (self.days[event.data[FIELD_DAY]][key] == '' or
                                        self.days[event.data[FIELD_DAY]][key] < event.data[key]):
                    self.days[event.data[FIELD_DAY]][key] = event.data[key]
                event.data[key + '_DT'] = event.data[key]

            # if self.data[FIELD_FIXED] == 'Yes' and isinstance(self.data[FIELD_TIME] > 0, (int, float)) and self.data[FIELD_START] == '':

            total[event.data[FIELD_TYPE]] += event.data[FIELD_TIME]
            total['Total'] += event.data[FIELD_TIME]

        for day in self.days:
            if isinstance(self.days[day]['Stop'], str) and self.days[day]['Stop'] == '':
                self.days[day]['Time_Range'] = ''
                self.days[day]['Start'] = ''
                self.days[day]['Stop'] = ''
                continue

            self.days[day]['Time_Range'] = self.days[day]['Stop'] - self.days[day]['Start']
            self.days[day]['Start'] = self.days[day]['Start'].strftime("%I:%M %p")
            self.days[day]['Stop'] = self.days[day]['Stop'].strftime("%I:%M %p")

        percent = {}
        for event_type in VALID_FIELD_TYPES:
            percent[event_type] = "%0.1f%%" % (total[event_type] / total['Total'] * 100)
        percent['Total'] = ''

        self.days['Total'] = total
        self.days['Percent'] = percent

    def print_trip(self):
        backup_file = '.' + os.path.basename(self.file_name)
        shutil.copy(self.file_name, backup_file)

        field_widths = {}
        for field in FIELD_LIST:
            field_widths[field] = len(field)
        for event in self.events:
            temp_dict = event.get_str_dict()
            for field in FIELD_LIST:
                temp_len = len(temp_dict[field])
                if temp_len > field_widths[field]:
                    field_widths[field] = temp_len

        with open(self.file_name, 'w') as update_fh:
            update_fh.write(self.format_line(field_widths, dict(zip(FIELD_LIST, FIELD_LIST))))
            day = 0
            for event in self.events:
                if day != event.data[FIELD_DAY]:
                    update_fh.write(self.sep_line(field_widths))
                day = event.data[FIELD_DAY]
                update_fh.write(self.format_line(field_widths, event.get_str_dict()))
            update_fh.write(self.sep_line(field_widths))

            for event_type in VALID_FIELD_TYPES:
                update_fh.write("\n")
                update_fh.write(event_type + "\n")
                update_fh.write(self.sep_line(field_widths))
                for event in self.events:
                    if event.data[FIELD_TYPE] == event_type:
                        update_fh.write(self.format_line(field_widths, event.get_str_dict()))
                update_fh.write(self.sep_line(field_widths))

            update_fh.write("\n")
            update_fh.write("Time Spent\n")
            update_fh.write(print_dict(dict_of_dicts=self.days, key='Day'))

    def validate(self):
        errors = 0
        error_buffer = ''

        for day in self.days:
            if day in ['Total', 'Percent']:
                continue

            if self.days[day]['Meals'] < 3:
                errors += 1
                error_buffer += "Day %s only has %d meals\n" % (day, self.days[day]['Meals'])


            while True:
                counter = 1
                last_end_time_counter = 1
                last_end_time = self.events[self.days[day]['First_Event']].data[FIELD_STOP_DT]

                restart = False
                for event_idx in range(self.days[day]['First_Event'] + 1, self.days[day]['Last_Event'] + 1):
                    counter += 1

                    if last_end_time != '' and \
                            self.events[event_idx].data[FIELD_START_DT] != '' and \
                            last_end_time > self.events[event_idx].data[FIELD_START_DT]:
                        errors += 1
                        error_buffer += "Day %s previous event (idx %d) starts after event (idx %d) stops (%s > %s)\n" % \
                                        (day, last_end_time_counter, counter, last_end_time.strftime("%I:%M %p"),
                                         self.events[event_idx].data[FIELD_START].strftime("%I:%M %p"))
                    elif self.events[event_idx].data[FIELD_START] != '' and last_end_time != '' and \
                            self.events[event_idx].data[FIELD_START] != last_end_time:
                        print("GAP!!! Day %s idx %d to %d (%s - %s)" %
                              (day, last_end_time_counter, counter, last_end_time,
                               self.events[event_idx].data[FIELD_START]))
                        trip_event = TripEvent(0, {
                            FIELD_IDX: 0,
                            FIELD_EVENT_IDX: 0,
                            FIELD_DAY: self.events[event_idx].data[FIELD_DAY],
                            FIELD_DATE: self.events[event_idx].data[FIELD_DATE],
                            FIELD_TYPE: FIELD_TYPE_FREE,
                            FIELD_WHERE: self.events[event_idx].data[FIELD_WHERE],
                            FIELD_DESCRIPTION: '',
                            FIELD_NOTES: '',
                            FIELD_TIME: str((self.events[event_idx].data[FIELD_START] - last_end_time).total_seconds() / 3600),
                            FIELD_FIXED: 'No',
                            FIELD_START: last_end_time.strftime("%I:%M %p"),
                            FIELD_STOP: self.events[event_idx].data[FIELD_START].strftime("%I:%M %p"),
                        })
                        trip_event.data[FIELD_START_DT] = last_end_time
                        trip_event.data[FIELD_STOP_DT] = self.events[event_idx].data[FIELD_START]
                        self.events.insert(event_idx, trip_event)
                        self.days[day]['Last_Event'] += 1
                        int_day = int(day)
                        for next_day in self.days:
                            if next_day in ['Total', 'Percent']:
                                continue

                            if int(next_day) > int_day:
                                self.days[next_day]['First_Event'] += 1
                                self.days[next_day]['Last_Event'] += 1

                        restart = True
                        break

                    if self.events[event_idx].data[FIELD_TIME] > 0 and self.events[event_idx].data[FIELD_START] == '' and \
                            last_end_time != '':
                        self.events[event_idx].data[FIELD_START] = last_end_time
                        # self.events[event_idx].data[FIELD_START] = last_end_time.strftime("%I:%M %p")
                        self.events[event_idx].data[FIELD_STOP] = \
                            last_end_time + datetime.timedelta(hours=self.events[event_idx].data[FIELD_TIME])
                        # self.events[event_idx].data[FIELD_STOP] = \
                        #     self.events[event_idx].data[FIELD_STOP_DT].strftime("%I:%M %p")
                        last_end_time = self.events[event_idx].data[FIELD_STOP_DT]
                        last_end_time_counter = counter
                    elif self.events[event_idx].data[FIELD_STOP_DT] != '':
                        last_end_time = self.events[event_idx].data[FIELD_STOP_DT]
                        last_end_time_counter = counter

                if restart is False:
                    break

            # if self.days[day]['']

        if errors > 0:
            print("\n\nErrors\n-------------------------------------------------------------------")
            print(error_buffer)
            sys.exit(1)

    def format_line(self, field_widths, format_data):
        buffer = '|'
        for field in FIELD_LIST:
            if field not in format_data:
                raise Exception("Field '%s' not found in data", field)
            temp_format = ' %-' + str(field_widths[field]) + 's |'
            value = format_data[field]
            if value is None:
                value = ''
            buffer += temp_format % value
        return buffer + "\n"

    def sep_line(self, field_widths):
        buffer = '|'
        for field in FIELD_LIST:
            buffer += '-' + '-' * field_widths[field] + '-|'
        return buffer + "\n"


class TripEvent:
    def __init__(self, line, event_dict):
        self.line = line
        self.data = {}
        self.data_str = {}
        try:
            for field in FIELD_LIST:
                if field not in event_dict:
                    print("Line:%d missing field:'%s'" % (line, field))
                    sys.exit(1)

                if field in [FIELD_DAY]:
                    self.data[field] = int(event_dict[field])

                if field == FIELD_TYPE:
                    if event_dict[field] not in VALID_FIELD_TYPES:
                        raise Exception("Invalid field type '%s'" % event_dict[field])
                    self.data[field] = event_dict[field]

                elif field == FIELD_TIME:
                    temp = event_dict[field]
                    if temp.isnumeric():
                        self.data[field] = int(temp)
                    elif temp == '':
                        self.data[field] = 0
                    elif '.' in temp:
                        tokens = temp.split('.')
                        self.data[field] = float(temp)
                    elif ':' in temp:
                        tokens = temp.split(':')
                        self.data[field] = int(tokens[0]) + int(tokens[1]) / 60
                    else:
                        raise Exception("Invalid time format")

                elif field in [FIELD_START, FIELD_STOP]:
                    temp = event_dict[field]
                    dt_formats = ['%I:%M %p', '%I:%M:%S %p', '%H:%M', '%H:%M:%S']
                    if temp == '':
                        self.data[field] = ''
                        continue

                    self.data[field] = None
                    for dt_format in dt_formats:
                        try:
                            self.data[field] = datetime.datetime.strptime(temp, dt_format)
                            self.data[field].replace(second=0)
                            break
                        except Exception as error_text:
                            pass

                    if self.data[field] is None:
                        raise Exception("Unable to parse datetime")

                elif field == FIELD_FIXED:
                    if event_dict[field] == '':
                        event_dict[field] = 'No'
                    elif event_dict[field].lower() not in ['yes', 'no']:
                        raise ValueError("Invalid fixed value '%s'" % event_dict[field])

                    self.data[field] = event_dict[field].capitalize()

                else:
                    self.data[field] = event_dict[field]

        except Exception as error_text:
            print("Failed to parse line:%d field:'%s' value:%s - %s" % (line, field, event_dict[field], error_text))
            sys.exit(1)

        if self.data[FIELD_TIME] == 0 and self.data[FIELD_START] != '' and self.data[FIELD_STOP] != '':
            self.data[FIELD_TIME] = (self.data[FIELD_STOP] - self.data[FIELD_START]).total_seconds() / 3600

    def get_str_dict(self):
        temp_dict = {}
        for field in FIELD_LIST:
            if isinstance(self.data[field], str) and self.data[field] == '':
                temp_dict[field] = str(self.data[field])
            elif field in [FIELD_START, FIELD_STOP]:
                temp_dict[field + '_DT'] = self.data[field]
                temp_dict[field] = self.data[field].strftime("%I:%M %p")
            elif field == FIELD_TIME and self.data[field] == 0:
                temp_dict[field] = ''
            elif field == FIELD_DATE:
                temp_dict[field] = self.data[field].strftime("%m/%d/%y, %a")
            else:
                temp_dict[field] = str(self.data[field])
        return temp_dict


def print_dict(list_of_dicts=None, dict_of_dicts=None, field_order=None, separator='|', key='Key'):
    widths = {}

    try:
        if field_order is None:
            if list_of_dicts is not None:
                field_order = list(list_of_dicts[0].keys)
            elif dict_of_dicts is not None:
                first_record = list(dict_of_dicts.keys())[0]
                field_order = list(dict_of_dicts[first_record].keys())

        if dict_of_dicts is not None and list_of_dicts is None:
            list_of_dicts = []
            field_order = [key] + field_order
            for dict_key in dict_of_dicts:
                dict_of_dicts[dict_key][key] = dict_key
                list_of_dicts.append(dict_of_dicts[dict_key])

        # Calculate field widths
        for row in list_of_dicts:
            if len(widths) == 0:
                for field in row:
                    widths[field] = len(field)

            for field in row:
                width = len(str(row[field]))
                if width > widths[field]:
                    widths[field] = width

        for field in field_order:
            if field not in widths:
                raise Exception("Invalid field '%s'" % field)

        field_format = separator
        sep_line = separator
        for field in field_order:
            field_format += ' %-' + str(widths[field]) + 's ' + separator
            sep_line += ' ' + '-' * widths[field] + ' ' + separator
        field_format += '\n'
        sep_line += '\n'

        buffer = sep_line
        buffer += field_format % tuple(field_order)
        buffer += sep_line
        for row in list_of_dicts:
            output = []
            for field in field_order:
                if field in row:
                    output.append(row[field])
                else:
                    output.append('')
            buffer += field_format % tuple(output)
        buffer += sep_line
    except Exception as error_text:
        print("print_dict encountered an error - %s\n%s" %
              (error_text, json.dumps(list_of_dicts, indent=4, default=str)))
        raise Exception(error_text)

    return buffer


if __name__ == "__main__":
    trip_obj = Trip(sys.argv[1])
    trip_obj.print_trip()
    trip_obj.validate()
    trip_obj.print_trip()
    trip_obj.validate()



