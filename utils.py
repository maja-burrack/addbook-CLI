from datetime import datetime, date
import json

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%B %d, %Y")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                return datetime.strptime(date_str, "%Y")
            except ValueError:
                try:
                    return datetime.strptime(date_str, "%B %Y")
                except:
                    try:
                        return datetime.strptime(date_str, "%Y")
                    except:
                        return date(1000, 1, 1)

def unique_list_of_dicts(lst):
    unique_dicts = list({json.dumps(d, sort_keys=True) for d in lst})
    unique_dicts = [json.loads(d) for d in unique_dicts]
    return unique_dicts