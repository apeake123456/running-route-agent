"""
Step 1: a minimal MCP server with ONE tool.

Goal: prove you can define a tool with @mcp.tool() and run the server
without errors. It won't DO anything visible yet — no client is
connecting to it. That's expected. We wire up a client in step 2.

Run it with:
    python mcp_server.py
It should just sit there (waiting for a client over stdio). Ctrl+C to stop.
"""

from geopy.geocoders import Nominatim
from mcp.server.fastmcp import FastMCP
import math 
import random 
import requests
import sys

# TODO 1: create the server instance.
# This name shows up when a client asks "what server am I talking to".
# mcp = FastMCP("...")

mcp = FastMCP("mcp-route-planner")

# TODO 2: create a geocoder.
# Nominatim needs a user_agent string (any identifying string works,
# e.g. "my_route_agent") — it's just how OpenStreetMap tracks usage.
# geolocator = Nominatim(user_agent="...")
geolocator = Nominatim(user_agent = "my_route_agent")

# TODO 3: write the tool.
#

# Things to get right:
# - The @mcp.tool() decorator is what makes this function callable by
#   an MCP client. Without it, it's just a normal Python function.
# - Type hints on the parameters (query: str) matter — MCP uses them to
#   build the schema a client sees, similar to how you'd document an
#   API endpoint's expected input.
# - The docstring matters too — later, when Claude is choosing between
#   several tools, THIS is what it reads to decide whether to call it.
#   Write it like you're explaining to someone (or something) who's
#   never seen your code what this does and when to use it.
# - Return a dict, not a raw object — geopy's location object isn't
#   JSON-serializable, so pull out .latitude, .longitude, .address.
# - Handle the "not found" case. geolocator.geocode() returns None if
#   it can't resolve the query — don't let that crash, return something
#   like {"error": "..."} instead.
#
# @mcp.tool()
# def geocode(query: str) -> dict:
#     """..."""
#     ...

@mcp.tool()
def geocode(query: str) -> dict:
    """Look up a place name and return its coordinates"""
    location = geolocator.geocode(query)
    if location is None: 
        return {"error" : "unable to find location"}
    return {
        "lat": location.latitude,
        "long" : location.longitude,
        "display_name" : location.address

    }



def destination_point(lat, lon, bearing_deg, dist_km):

    """Given a start point, a compass bearing (degrees), and a distance
    (km), return the (lat, lon) you'd end up at. This is a standard
    great-circle formula — you don't need to derive it, just wire it up."""
    R = 6371.0  # Earth's radius in km — this is a constant, leave as-is
 
    # TODO A: convert bearing_deg, lat, and lon from degrees to radians.
    # Python's math module has a function for exactly this — check
    # math.<tab> in VS Code if you're not sure of the name.
    bearing = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
 
    # This formula is given to you as-is — just make sure the variable
    # names above (bearing, lat1) match what you named them.
    lat2 = math.asin(
        math.sin(lat1) * math.cos(dist_km / R)
        + math.cos(lat1) * math.sin(dist_km / R) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(dist_km / R) * math.cos(lat1),
        math.cos(dist_km / R) - math.sin(lat1) * math.sin(lat2),
    )
 
    # TODO B: the formula above works in radians, but we want to RETURN
    # degrees (to match how you've been using lat/lon everywhere else).
    # Convert lat2 and lon2 back to degrees and return them as a tuple.
    return (math.degrees(lat2), math.degrees(lon2))
 
 
# TODO C: this is the tool itself. Decorate it the same way you did
# geocode. Parameters: start_lat (float), start_lon (float),
# target_km (float). Returns a dict.
#
# The approach:
#   1. Pick a radius: target_km / (2 * math.pi) — this comes from
#      circumference = 2*pi*radius, so a loop of roughly target_km
#      should have about this radius.
#   2. Pick a random starting angle: random.uniform(0, 360)
#   3. Generate 5 waypoints spaced 72 degrees apart around that circle
#      (5 points, so 360/5 = 72 degrees between each), using
#      destination_point() for each one.
#   4. Build a list of (lat, lon) tuples: the start point FIRST, then
#      your 5 generated waypoints.
#   5. We'll turn that into a real route via OSRM as a separate step —
#      for now, just return the waypoints so you can see them.
#
@mcp.tool()
def generate_loop_waypoints(start_lat: float, start_lon: float, target_km: float) -> dict:     
    """Generate waypoints scattered in a rough circle around a starting
    point, sized to produce a loop of roughly target_km. Returns a list
    of (lat, lon) points including the start point first. This is a
    step toward a full route — the points aren't snapped to real streets yet."""
    radius_km = target_km / (2 * math.pi)
    base_angle = random.uniform(0, 360)
    waypoints = [(start_lat, start_lon)]
    for i in range(5):
        angle = base_angle + 72 * i
        point = destination_point(start_lat, start_lon, angle, radius_km)
        waypoints.append(point)
    return {"waypoints": waypoints}




# Add this as a new tool in step1_mcp_server_skeleton.py, below
# generate_loop_waypoints.

# TODO A: build the coordinate string OSRM expects.
# OSRM wants: "lon1,lat1;lon2,lat2;lon3,lat3;..."
# Note the order: LONGITUDE first, then latitude — backwards from how
# you've been using (lat, lon) tuples everywhere else. This catches
# almost everyone out at least once.
#
# Given `waypoints` — a list of (lat, lon) tuples like the ones your
# generate_loop_waypoints tool already returns — build that string.
# A list comprehension + ";".join(...) is the clean way to do this:
#
# coord_str = ";".join(f"{lon},{lat}" for lat, lon in waypoints)


@mcp.tool()
def snap_to_roads(waypoints: list) -> dict:
    """Take a list of [lat, lon] waypoints (like the output of
    generate_loop_waypoints) and turn them into a real, street-following
    loop route using OSRM's routing engine. Returns the actual route
    geometry and total distance."""

    # TODO A goes here (see above)
    coord_str = ";".join(f"{lon},{lat}" for lat, lon in waypoints)

    # TODO B: build the request URL.
    # OSRM's "trip" endpoint, with roundtrip=true so it returns to the
    # start, and geometries=geojson so we get coordinates back in a
    # format we can easily use.
    url = (
        f"https://router.project-osrm.org/trip/v1/driving/{coord_str}"
        "?roundtrip=true&overview=full&geometries=geojson"
    )

    # TODO C: make the request and handle failure.
    # requests.get(url, timeout=15) — same pattern you'll want to get
    # comfortable with for any external API call. Check resp.ok before
    # trying to use the response — if it's not ok, return a clean error
    # dict rather than letting it crash (same lesson as geocode).
    #
    try:
        print(url, file=sys.stderr)
        resp = requests.get(url, timeout=15)
    except Exception as e:
        return {"error": f"Request failed: {e}"}
    
    if not resp.ok:
        return {"error": f"OSRM returned status {resp.status_code}"}

    # TODO D: parse the response.
    # resp.json() turns the response into a Python dict. OSRM's trip
    # response has this rough shape (you may want to print(data) once
    # here just to SEE it before writing code against it — a good habit
    # any time you're using an API for the first time):
    #
    # {
    #   "code": "Ok",
    #   "trips": [
    #     {
    #       "distance": 5234.5,   <- meters
    #       "geometry": {
    #         "coordinates": [[lon, lat], [lon, lat], ...]
    #       }
    #     }
    #   ]
    # }
    #
    data = resp.json()
    print(data, file=sys.stderr)
    if data.get("code") != "Ok" or not data.get("trips"):
         return {"error": "Could not find a route through these points"}
    
    trip = data["trips"][0]

    # TODO E: return something useful.
    # The coordinates come back as [lon, lat] pairs (OSRM's convention
    # again) — flip them back to [lat, lon] to stay consistent with
    # everything else in this project. distance comes back in meters —
    # you'll probably want to convert to km too.
    #
    route_coords = [[point[1], point[0]] for point in trip["geometry"]["coordinates"]]
    return {
         "distance_km": round(trip["distance"] / 1000, 2),
         "coords": route_coords,
     }


if __name__ == "__main__":
    # TODO 4: start the server.
    # There's one obvious method on `mcp` for this — check the FastMCP
    # docs/autocomplete if you're not sure of the name.
    mcp.run()
