import json

import pytest
from device import Device

STATUS_CODE_OK = 200
STATUS_CODE_NOT_FOUND = 404
INVALID_DEVICE_ID_LIST = ['Andreea', '', '2s$#%#', 'A' * 100, 'DEVICE1']
VALID_DEVICE_ID_LIST = ['device1', 'device2', 'device3']
SAMPLE_DEVICE_ID = 'device1'
DEVICE_NOT_FOUND_ERR = "Device not found"


@pytest.mark.asyncio
async def test_get_devices(client, redis_client):
    await redis_client.set("device:device1", Device(id="device1", name="DUT1-Cisco", type="Router",
                                                    status="online", command_history=[]).model_dump_json())
    await redis_client.set("device:device2", Device(id="device2", name="DUT2-Cisco", type="Switch",
                                                    status="offline", command_history=[]).model_dump_json())
    response = client.get("/devices")
    assert response.status_code == STATUS_CODE_OK, f"API failed with status: {response.status_code}"
    devices = response.json()
    assert len(devices) >= 1, f"Expected at least 1 device, but got {len(devices)}. devices={devices}"

    # Make sure all returned devices are present in Redis
    for device in devices:
        data = await redis_client.get(f"device:{device['id']}")
        assert data is not None, f"Redis data not found for device ID: {device['id']} ({device.get('name', 'no name')})"


@pytest.mark.asyncio
async def test_get_device(client, redis_client):
    await redis_client.set("device:device1", Device(id="device1", name="DUT1-Cisco", type="Router",
                                                    status="online", command_history=[]).model_dump_json())
    response = client.get(f"/devices/{SAMPLE_DEVICE_ID}")
    assert response.status_code == STATUS_CODE_OK, f"API failed with status: {response.status_code}"
    device = response.json()

    # Make sure the returned device is present in Redis
    data = await redis_client.get(f"device:{device['id']}")
    assert data is not None, f"Redis key 'device:{device['id']}' returned None. Device ID: {device['id']}, device: {device} "


@pytest.mark.asyncio
async def test_get_device_details(client, redis_client):
    await redis_client.set("device:device1", Device(id="device1", name="DUT1-Cisco", type="Router",
                                                    status="online", command_history=[]).model_dump_json())
    response = client.get(f"/devices/{SAMPLE_DEVICE_ID}")
    assert response.status_code == STATUS_CODE_OK, f"API failed with status: {response.status_code}"
    expected_response = {
        'id': 'device1',
        'name': 'DUT1-Cisco',
        'type': 'Router',
        'status': 'online',
        'command_history': []
    }

    assert sorted(response.json().items()) == sorted(expected_response.items()), \
        f"Unexpected response. Got: {response.json()}, Expected: {expected_response}"


# Test GET response for invalid device IDs
@pytest.mark.parametrize("device_id", INVALID_DEVICE_ID_LIST)
@pytest.mark.asyncio
async def test_get_devices_invalid(client, device_id):
    response = client.get(f"/devices/{INVALID_DEVICE_ID_LIST}")
    assert response.status_code == STATUS_CODE_NOT_FOUND
    assert response.json()["detail"] == DEVICE_NOT_FOUND_ERR


# Test GET response for invalid device IDs
@pytest.mark.parametrize("device_id", VALID_DEVICE_ID_LIST)
@pytest.mark.asyncio
async def test_get_devices_valid(client, redis_client, device_id):
    await redis_client.set("device:device1", Device(id="device1", name="DUT1-Cisco", type="Router",
                                                    status="online", command_history=[]).model_dump_json())
    await redis_client.set("device:device2", Device(id="device2", name="DUT1-Juniper", type="Switch",
                                                    status="online", command_history=[]).model_dump_json())
    await redis_client.set("device:device3", Device(id="device3", name="DUT1-PaloAlto", type="Firewall",
                                                    status="online", command_history=[]).model_dump_json())

    response = client.get(f"/devices/{device_id}")
    assert response.status_code == STATUS_CODE_OK, f"API failed with status: {response.status_code}"


@pytest.mark.asyncio
async def test_delete_device(client, redis_client):
    test_device_id = "dev100"
    device = Device(id=test_device_id, name="DUT1-Cisco", type="Router",
                    status="online", command_history=[])

    await redis_client.set(f"device:{test_device_id}", device.model_dump_json())

    # Delete the device
    response = client.delete(f"/devices/{test_device_id}")
    assert response.status_code == STATUS_CODE_OK, f"API failed with status: {response.status_code}"
    assert response.json()["msg"] == "Device dev100 deleted", f"Unexpected deletion message. Expected: 'Device " \
                                                              f"dev100 deleted', Got: '{response.json().get('msg')}' "


@pytest.mark.asyncio
async def test_delete_device_non_existent(client, redis_client):
    test_device_id = "dev100"

    # Delete the non-existing device
    response = client.delete(f"/devices/{test_device_id}")
    assert response.status_code == STATUS_CODE_NOT_FOUND
    assert response.json()["detail"] == DEVICE_NOT_FOUND_ERR


@pytest.mark.asyncio
async def test_send_command(client, redis_client):
    sample_device_id = "device1"
    await redis_client.set("device:device1", Device(id="device1", name="DUT1-Cisco", type="Router",
                                                    status="offline", command_history=[]).model_dump_json())
    command = {'action': 'status', 'value': 'online'}
    response = client.post(f"/devices/{sample_device_id}/command", json=command)
    assert response.status_code == STATUS_CODE_OK

    # Verify command was stored in Redis
    raw_device = await redis_client.get(f"device:{sample_device_id}")
    assert raw_device is not None
    updated_device = Device(**json.loads(raw_device))
    assert len(updated_device.command_history) > 0
    assert updated_device.command_history[0] == "Set status to online"


# OpenAPI - validation of endpoints against OpenAPI schema
@pytest.mark.asyncio
async def test_openapi_endpoints_present(client):
    response = client.get("/openapi.json")
    assert response.status_code == STATUS_CODE_OK
    schema = response.json()

    paths = schema["paths"]
    assert "/devices" in paths
    assert "get" in paths["/devices"]

    assert "/devices/{device_id}" in paths
    assert "get" in paths["/devices/{device_id}"]

    assert "/devices/{device_id}" in paths
    assert "delete" in paths["/devices/{device_id}"]

    assert "/devices/{device_id}/command" in paths
    assert "post" in paths["/devices/{device_id}/command"]

    response = client.get("/devices")
    assert response.status_code == STATUS_CODE_OK
