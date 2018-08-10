# Required packages (Python)

* polyline
* postgis
* psycopg2
* psycopg2-binary

# Load OSM pbf into Postgis

1. Download the pbf file (for example: https://download.geofabrik.de/south-america/brazil.html)
2. Run a Postgis instance (docker):

```
sudo docker run -d --name postgis -e POSTGRES_PASSWORD=password -e POSTGRES_DB=gis -e POSTGRES_USER=user -e ALLOW_IP_RANGE=0.0.0.0/0 -p 5432:5432 -d mdillon/postgis
``` 

3. Install osm2pgsql and run:

```
osm2pgsql -U user -W brazil-latest.osm.pbf -P 5432 -H 127.0.0.1 -C 4000 --latlong
```

4. Update your $HOME/.pgpass file, adding the credentials as following:

```
<ip>:<port>:<database>:<user>:<password>
``` 

5. Login:

```
psql -p 5432 -U admin -d gis -W -h 127.0.0.1
```

6. A simple query to get the polygon for the neighborhood called Derby, from Recife, PE, Brazil:

```
select st_astext(way) from planet_osm_polygon where name = 'Derby';
```
# Understanding the OSM database

As far as I understand, the planet_osm_polygon table contains the most important data: the polygon that represents a region (column: way), its name (column: name), its administrative level (column: admin_level, more on that later) and the id (column: osm_id).

In Brazil, an administrative level 8 region is usually a city; level 9 or 10 represents a neighborhood.

# Getting the polygon for a given region

My motivation in writing this project was to find all neighborhood polygons for the city of Recife, PE, Brazil. To accomplish that, I did the following:

Run the following query to find the osm_id for the city:

```
select osm_id, admin_level from planet_osm_polygon where name ='Recife';
```

The result should be something like this:

```
  osm_id   | admin_level 
-----------+-------------
   -303585 | 8
  -7383972 | 10
  -6188367 | 9
 128378262 | 
```

So I took the id -303585; also, the neighborhood regions for Recife city have administrative level = 10, so I run:

```
python query_postgis.py --osm-id -303585  -A 10
```

There is also an option to output encoded polyline, useful to plot all polygons in a site like http://developer.onebusaway.org/maps/:

```
python query_postgis.py --osm-id -303585  -A 10 --polyline | xclip -selection clipboard
```


