from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

# Load database.py with a tiny HA core stub so storage behavior can be tested
# outside a running Home Assistant instance.
import types
ha=types.ModuleType('homeassistant'); core=types.ModuleType('homeassistant.core')
class HomeAssistant: pass
core.HomeAssistant=HomeAssistant; ha.core=core
sys.modules.setdefault('homeassistant',ha); sys.modules.setdefault('homeassistant.core',core)
import importlib.util
spec=importlib.util.spec_from_file_location("vm_database", ROOT/"custom_components/verbrauchsmonitor/database.py")
database=importlib.util.module_from_spec(spec); spec.loader.exec_module(database)

class Config:
    def __init__(self,path): self._path=path
    def path(self,*parts): return str(self._path.joinpath(*parts))
class Hass:
    def __init__(self,path): self.config=Config(path)

def test_r039_bookings_migrate_unresolved_once(tmp_path):
    hass=Hass(tmp_path)
    old=[{'id':'abc','date':'2026-01-15','amount':75,'booking_type':'payment','description':'Nachzahlung'}]
    first=database.migrate_legacy_bookings(hass,'entry1',old)
    assert len(first['bookings'])==1
    item=first['bookings'][0]
    assert item['status']=='unresolved' and item['meter_id'] is None and item['direction'] is None
    assert item['comment']=='Nachzahlung' and item['amount']==75
    second=database.migrate_legacy_bookings(hass,'entry1',old)
    assert len(second['bookings'])==1

def test_monthly_rate_change_applies_from_effective_month(tmp_path):
    hass=Hass(tmp_path)
    database.record_advance_rate(hass,meter_id='m1',direction='consumption',contract_id='c1',effective_from='2026-01',amount=100)
    database.record_advance_rate(hass,meter_id='m1',direction='consumption',contract_id='c1',effective_from='2026-04',amount=75)
    database.record_advance_rate(hass,meter_id='m1',direction='consumption',contract_id='c1',effective_from='2026-10',amount=50)
    data=database.load_data(hass)
    assert database.calculate_scheduled_advances(data,meter_id='m1',direction='consumption',start_month='2026-01',end_month='2026-12')==900

def test_physical_meter_periods_are_historical_and_directional(tmp_path):
    hass=Hass(tmp_path)
    record=database.record_physical_meter_period(hass,{'meter_id':'m1','direction':'feed_in','physical_meter_number':'F-100','installed_at':'2026-01-01','start_reading':12.5,'removed_at':'2026-06-01','end_reading':300.0})
    data=database.load_data(hass)
    assert data['physical_meter_periods'][0]['id']==record['id']
    assert data['physical_meter_periods'][0]['direction']=='feed_in'

def test_new_booking_requires_logical_meter_and_direction(tmp_path):
    hass=Hass(tmp_path)
    try:
        database.add_booking(hass,{'date':'2026-02-01','amount':10,'booking_type':'payment'})
    except ValueError as err:
        assert 'Zähler' in str(err)
    else:
        raise AssertionError('Unzugeordnete Zahlung wurde akzeptiert')


def test_monthly_advance_override_changes_only_selected_month_and_keeps_audit(tmp_path):
    hass=Hass(tmp_path)
    database.record_monthly_advance(hass,meter_id="m1",direction="consumption",contract_id="c1",month="2026-04",amount=180)
    database.record_monthly_advance(hass,meter_id="m1",direction="consumption",contract_id="c1",month="2026-05",amount=180)
    database.record_monthly_advance(hass,meter_id="m1",direction="consumption",contract_id="c1",month="2026-04",amount=210)
    data=database.load_data(hass)
    assert database.get_monthly_advance(data,meter_id="m1",direction="consumption",month="2026-04",default=100)==210
    assert database.get_monthly_advance(data,meter_id="m1",direction="consumption",month="2026-05",default=100)==180
    assert sum(1 for x in data["monthly_advances"] if x.get("month")=="2026-04") == 2
    assert next(x for x in data["monthly_advances"] if x.get("month")=="2026-04")["superseded"] is True


def test_assigned_actual_advance_bookings_survive_reload_and_remain_assigned(tmp_path):
    hass=Hass(tmp_path)
    for month in ("2026-08-05", "2026-09-05", "2026-10-05", "2026-11-05"):
        database.add_booking(hass, {
            "meter_id":"m1", "direction":"consumption", "contract_id":"c1",
            "date":month, "amount":"200.00", "booking_type":"advance",
            "status":"assigned",
        })
    reloaded=database.load_data(hass)
    paid=database.assigned_bookings(hass, "m1", "consumption")
    assert len(paid)==4
    assert sum(float(item["amount"]) for item in paid)==800.0
    assert len(reloaded["bookings"])==4


def test_legacy_assigned_advance_is_migrated_and_preserved_across_setup(tmp_path):
    hass=Hass(tmp_path)
    meters=[{"id":"m1","contract_id":"c1","consumption_entity":"sensor.grid"}]
    legacy=[{
        "id":"legacy-800","date":"2026-08-05","amount":"800.00",
        "booking_type":"advance","direction":"consumption","meter_id":"m1",
    }]
    first=database.migrate_legacy_bookings(hass,"entry1",legacy,meters)
    second=database.migrate_legacy_bookings(hass,"entry1",legacy,meters)
    assert len(first["bookings"])==1
    assert len(second["bookings"])==1
    item=database.assigned_bookings(hass,"m1","consumption")[0]
    assert item["status"]=="assigned"
    assert item["amount"]=="800.00"
