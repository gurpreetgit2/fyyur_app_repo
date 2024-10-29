#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import (
   Flask, 
   jsonify, 
   render_template, 
   request, 
   Response, 
   flash, 
   redirect, 
   url_for
  )
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
from datetime import datetime
from models import db, Venue, Artist, Show
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)

migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():

  areas = Venue.query.with_entities(Venue.city, Venue.state).distinct().all()
  data=[]
  for area in areas:
        venues_in_area = Venue.query.filter_by(city=area.city, state=area.state).all()
        
        # Format each venue entry with the required fields
        venue_data = [{
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": venue.num_upcoming_shows()  # Assuming you have this method implemented in your model
        } for venue in venues_in_area]
        
        # Append area data with venues
        data.append({
            "city": area.city,
            "state": area.state,
            "venues": venue_data
        })
  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # Get the search term from the form
    search_term = request.form.get('search_term', '')

    # Query the database for venues with names that match the search term
    matched_venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()

    # Format the response
    response = {
        "count": len(matched_venues),
        "data": []
    }
    
    # Populate response data with each venue's details
    for venue in matched_venues:
        response["data"].append({
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": venue.num_upcoming_shows()  # Assuming this method is in your Venue model
        })

    # Render the results with the search term
    return render_template('pages/search_venues.html', 
                           results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # Query the database for the venue with the specified venue_id
    venue = Venue.query.get(venue_id)
    if not venue:
        return render_template('errors/404.html'), 404

    # Prepare past and upcoming shows
    past_shows = []
    upcoming_shows = []
    
    # Query related shows and classify them based on their start time
    for show in venue.shows:
        show_data = {
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": show.show_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
        if show.show_time < datetime.now():
            past_shows.append(show_data)
        else:
            upcoming_shows.append(show_data)
    
    # Prepare the data dictionary to pass to the template
    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website_link": venue.website_link,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }
    
    # Render the template with the venue data
    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  try:
    # Extract data from the incoming JSON request
    data = request.get_json()

    # Check if genres is already a list; if not, split
    genres = data.get('genres')
    if isinstance(genres, str):
        genres = genres.split(',')  
    elif not isinstance(genres, list):
        genres = list(genres)  # Fallback if genres is formatted incorrectly


    # Create a new Venue object
    new_venue = Venue(
        name=data.get('name'),
        city=data.get('city'),
        state=data.get('state'),
        address=data.get('address'),
        phone=data.get('phone'),
        genres=genres,
        facebook_link=data.get('facebook_link'),
        image_link=data.get('image_link'),
        website_link=data.get('website_link'),
        seeking_talent=data.get('seeking_talent') == 'y',
        seeking_description=data.get('seeking_description')
    )

        # Add the new venue to the session and commit it to the database
    db.session.add(new_venue)
    db.session.commit()

    # Return a success message
    return jsonify({
        'success': True,
        'venue': {
            'id': new_venue.id,
            'name': new_venue.name,
            'city': new_venue.city,
            'state': new_venue.state,
            'address': new_venue.address,
            'phone': new_venue.phone,
            'genres': new_venue.genres,
            'facebook_link': new_venue.facebook_link,
            'image_link': new_venue.image_link,
            'website_link': new_venue.website_link,
            'seeking_talent': new_venue.seeking_talent,
            'seeking_description': new_venue.seeking_description
        }
    }), 201  # HTTP status code for created

  except Exception as e:
      # Rollback the session in case of an error
      db.session.rollback()
      print(f"Error creating venue: {e}")  # Log the error for debugging
      return jsonify({'success': False, 'error': str(e)}), 400  # HTTP status code for bad request
  
  finally:
    db.session.close()


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
      venue = Venue.query.get(venue_id)
      if not venue:
          return jsonify({"error": "Venue not found"}), 404

      db.session.delete(venue)
      db.session.commit()
      return jsonify({"success": True}), 200  # Respond with success status

  except Exception as e:
      db.session.rollback()
      print(f"Error deleting venue {venue_id}: {e}")
      return jsonify({"error": "An error occurred while deleting the venue."}), 500

  finally:
      db.session.close()

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # Fetch all artists from the database
  artists_query = Artist.query.all()

  # Prepare data for rendering
  data = [{
      "id": artist.id,
      "name": artist.name,
  } for artist in artists_query]

  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # Get the search term from the form
  search_term = request.form.get('search_term', '')
  # Query the database for venues with names that match the search term
  matched_artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()
  # Format the response
  response = {
      "count": len(matched_artists),
      "data": []
  }
  # Populate response data with each venue's details
  for artist in matched_artists:
      response["data"].append({
          "id": artist.id,
          "name": artist.name
      })
  return render_template('pages/search_artists.html', 
                         results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # Fetch the artist with the given artist_id
    artist = Artist.query.get(artist_id)

    if not artist:
        return render_template('errors/404.html'), 404  # Handle artist not found

    # Fetch the past shows for the artist
    past_shows_query = db.session.query(
        Show.venue_id,
        Venue.name.label("venue_name"),
        Venue.image_link.label("venue_image_link"),
        Show.show_time
    ).join(Venue).filter(Show.artist_id == artist_id).all()

    # Fetch the upcoming shows for the artist
    upcoming_shows_query = db.session.query(
        Show.venue_id,
        Venue.name.label("venue_name"),
        Venue.image_link.label("venue_image_link"),
        Show.show_time
    ).join(Venue).filter(Show.artist_id == artist_id).all()

    # Format past shows
    past_shows = [{
        "venue_id": show.venue_id,
        "venue_name": show.venue_name,
        "venue_image_link": show.venue_image_link,
        "start_time": show.show_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    } for show in past_shows_query]

    # Format upcoming shows
    upcoming_shows = [{
        "venue_id": show.venue_id,
        "venue_name": show.venue_name,
        "venue_image_link": show.venue_image_link,
        "start_time": show.show_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    } for show in upcoming_shows_query]

    # Prepare data for rendering
    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,  # Assuming genres are stored as a comma-separated string
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website_link": artist.website_link,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = Artist.query.get(artist_id)
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # Get the submitted data as JSON
    data = request.get_json()

    try:
      # Find the artist by ID
      artist = Artist.query.get(artist_id)
      
      # Update artist attributes with the form data
      artist.name = data.get('name')
      artist.city = data.get('city')
      artist.state = data.get('state')
      artist.phone = data.get('phone')
      artist.genres = data.get('genres')
      artist.facebook_link = data.get('facebook_link')
      artist.image_link = data.get('image_link')
      artist.website_link = data.get('website_link')
      artist.seeking_venue = data.get('seeking_venue') == 'y'
      artist.seeking_description = data.get('seeking_description')

      # Commit the changes to the database
      db.session.commit()

      # Redirect to the artist's page after update
      return jsonify({"success": True}), 200

    except Exception as e:
        # Roll back the session if there's an error
        db.session.rollback()
        print(f"Error: {e}")
        return jsonify({"error": "Could not update artist"}), 500
    finally:
        db.session.close()

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue = Venue.query.get(venue_id)
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  data = request.get_json()
  try:
    venue = Venue.query.get(venue_id)
    # update values for this above venue object
    venue.name = data.get('name')
    venue.city = data.get('city')
    venue.state = data.get('state')
    venue.address = data.get('address')
    venue.phone = data.get('phone')
    venue.genres = data.get('genres')
    venue.facebook_link = data.get('facebook_link')
    venue.image_link=data.get('image_link')
    venue.website_link=data.get('website_link')
    venue.seeking_talent=data.get('seeking_talent') == 'y'
    venue.seeking_description=data.get('seeking_description')

    # Commit the changes to the database
    db.session.commit()

    # Redirect to the artist's page after update
    return jsonify({"success": True}), 200

  except Exception as e:
    # Roll back the session if there's an error
    db.session.rollback()
    print(f"Error: {e}")
    return jsonify({"error": "Could not update artist"}), 500
  
  finally:
    db.session.close() 

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  try:
    # Extract data from the incoming JSON request
    data = request.get_json()

    # Check if genres is already a list; if not, split
    genres = data.get('genres')
    if isinstance(genres, str):
        genres = genres.split(',')  
    elif not isinstance(genres, list):
        genres = list(genres)  # Fallback if genres is formatted incorrectly

    # Create a new Venue object
    new_artist = Artist(
        name=data.get('name'),
        city=data.get('city'),
        state=data.get('state'),
        phone=data.get('phone'),
        genres=genres,
        facebook_link=data.get('facebook_link'),
        image_link=data.get('image_link'),
        website_link=data.get('website_link'),
        seeking_venue=data.get('seeking_venue') == 'y',
        seeking_description=data.get('seeking_description')
    )

        # Add the new venue to the session and commit it to the database
    db.session.add(new_artist)
    db.session.commit()

    # Return a success message
    return jsonify({
        'success': True,
        'artist': {
            'id': new_artist.id,
            'name': new_artist.name,
            'city': new_artist.city,
            'state': new_artist.state,
            'phone': new_artist.phone,
            'genres': new_artist.genres,
            'facebook_link': new_artist.facebook_link,
            'image_link': new_artist.image_link,
            'website_link': new_artist.website_link,
            'seeking_venue': new_artist.seeking_venue,
            'seeking_description': new_artist.seeking_description
        }
    }), 201  # HTTP status code for created

  except Exception as e:
      # Rollback the session in case of an error
      db.session.rollback()
      print(f"Error creating venue: {e}")  # Log the error for debugging
      return jsonify({'success': False, 'error': str(e)}), 400  # HTTP status code for bad request
  
  finally:
    db.session.close()


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # Query to fetch all shows, along with associated venue and artist data
    shows_data = db.session.query(
      Show.venue_id,
      Venue.name.label("venue_name"),
      Show.artist_id,
      Artist.name.label("artist_name"),
      Artist.image_link.label("artist_image_link"),
      Show.show_time
    ).join(Venue, Show.venue_id == Venue.id).join(Artist, Show.artist_id == Artist.id).all()

    # Format the data for rendering
    data = []
    for show in shows_data:
        data.append({
          "venue_id": show.venue_id,
          "venue_name": show.venue_name,
          "artist_id": show.artist_id,
          "artist_name": show.artist_name,
          "artist_image_link": show.artist_image_link,
          "start_time": show.show_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        })

    return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
   try:
    # Extract data from the incoming JSON request
    data = request.get_json()

    # create a new show obect
    new_show = Show(
       artist_id = data.get('artist_id'),
       venue_id = data.get('venue_id'),
       show_time = data.get('start_time')
    )
    db.session.add(new_show)
    db.session.commit()
    return jsonify({
       'success': True,
       'show':{
          'id':new_show.id,
          'venue_id':new_show.venue_id,
          'start_time':new_show.show_time
       }
    }), 201  # HTTP status code for created
   
   except Exception as e:
      db.session.rollback()
      print(f"Error creating venue: {e}")  # Log the error for debugging
      return jsonify({'success': False, 'error': str(e)}), 400  # HTTP status code for bad request
   
   finally: 
    db.session.close()     
  

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
# if __name__ == '__main__':
#     app.run()

# Or specify port manually:

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5001)

