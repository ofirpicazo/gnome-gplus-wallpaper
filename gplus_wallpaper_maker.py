#!/usr/bin/env python
# encoding: utf-8
"""
Script to create a Gnome slideshow wallpaper based on a G+ album.

@author: Ofir Picazo - ofirpicazo@gmail.com
@date: January 2015
"""

import argparse
import os
import random
import shutil
import sys
import urllib
import xml.etree.ElementTree as ET

from xml.dom import minidom


_BACKGROUND_PROPERTIES_DIR = os.path.expanduser(
    '~/.local/share/gnome-background-properties/')
_BACKGROUNDS_DIR = os.path.expanduser('~/.local/share/backgrounds/')
_GPHOTO_NS = 'http://schemas.google.com/photos/2007'
_MEDIA_NS = 'http://search.yahoo.com/mrss/'


def main():
  """Creates a Gnome slideshow wallpaper based on a G+ album."""

  parser = argparse.ArgumentParser()
  parser.add_argument(
      'album_url',
      help='URL to the Google+ API endpoint for the requested album. See: '
          + 'https://developers.google.com/picasa-web/docs/2.0/'
          + 'developers_guide_protocol#ListAlbumPhotos',
      type=str)
  parser.add_argument(
      '-d',
      '--duration_minutes',
      help='Number of minutes between wallpaper image updates.',
      type=int,
      default=30)
  parser.add_argument(
      '-r',
      '--randomize',
      help='Randomize the order of the images in the slideshow.',
      action='store_true')
  args = parser.parse_args()

  album_xml = minidom.parse(urllib.urlopen(args.album_url))
  album_name = album_xml.getElementsByTagNameNS(
      _GPHOTO_NS, 'name')[0].firstChild.nodeValue
  album_id = album_xml.getElementsByTagNameNS(
      _GPHOTO_NS, 'id')[0].firstChild.nodeValue
  album_dir = os.path.join(_BACKGROUNDS_DIR, album_id)

  # Recreate album directory, removes previously created slideshow and images.
  shutil.rmtree(album_dir, ignore_errors=True)
  os.makedirs(album_dir)

  # Create the background properties directory if it doesn't exist.
  try:
    os.makedirs(_BACKGROUND_PROPERTIES_DIR)
  except OSError as e:
    # Directory already exists.
    pass

  images = []

  # Download and save all the images in the album.
  media_content_elements = album_xml.getElementsByTagNameNS(
      _MEDIA_NS, 'content')
  _print_download_progress(len(media_content_elements), 0)

  for index, media_content in enumerate(media_content_elements):
    filepath = _save_image(media_content.getAttribute('url'), album_dir)
    images.append(filepath)
    _print_download_progress(len(media_content_elements), index + 1)
  print # We need to insert an extra new line here.

  if args.randomize:
    random.shuffle(images)

  # Create slideshow xml and save it in the same place as the images.
  slideshow_xml = _create_slideshow_xml(images, args.duration_minutes)
  slideshow_xml_filepath = os.path.join(album_dir, 'slideshow.xml')
  print 'Writing slideshow xml to: %s' % slideshow_xml_filepath
  slideshow_xml.write(slideshow_xml_filepath)

  # Create background properties xml file and save it in the correct location.
  bg_properties_xml = _create_background_properties_xml(
      album_name, slideshow_xml_filepath)
  bg_properties_xml_filepath = os.path.join(
      _BACKGROUND_PROPERTIES_DIR, album_id + '.xml')
  print 'Writing background properties to: %s' % bg_properties_xml_filepath
  with open(bg_properties_xml_filepath, 'w') as bg_properties_file:
    # encoding and doctype are needed on this file.
    bg_properties_file.write('<?xml version="1.0" encoding="UTF-8"?>'
        + '<!DOCTYPE wallpapers SYSTEM "gnome-wp-list.dtd">')
    bg_properties_xml.write(bg_properties_file, 'utf-8')

  print 'All done!'


def _print_download_progress(total, so_far):
  """Print image download progress in a single line."""

  sys.stdout.write('\rDownloading {0:d} images: {1:.0%}'.format(
      total, so_far / float(total)))
  sys.stdout.flush()


def _save_image(image_url, album_dir):
  """Downloads and stores an image to the album directory.

  Args:
    image_url: Url of the image to download (full size).
    album_dir: Local path of the directory to store the album images.

  Returns:
    A string representing the path to the saved image on local disk.
  """

  base_image_url, image_filename = image_url.rsplit('/', 1)
  download_url = '%s/s4096-d/%s' % (base_image_url, image_filename)
  local_filepath = os.path.join(album_dir, image_filename)
  urllib.urlretrieve(download_url, local_filepath)
  return local_filepath


def _create_slideshow_xml(images, duration_minutes):
  """Returns an ElementTree representing the slideshow XML.

  Args:
    images: A list of local file paths to the saved wallpaper images.
    album_dir: Path to the album directory on local disk.

  Returns:
    An ElementTree object with the contents of the slideshow XML.
  """

  background = ET.Element('background')
  # Set to some time in the past, but make sure to start at midnight.
  starttime = ET.SubElement(background, 'starttime')
  year = ET.SubElement(starttime, 'year')
  year.text = '2015'
  month = ET.SubElement(starttime, 'month')
  month.text = '01'
  day = ET.SubElement(starttime, 'day')
  day.text = '01'
  hour = ET.SubElement(starttime, 'hour')
  hour.text = '00'
  minute = ET.SubElement(starttime, 'minute')
  minute.text = '00'
  second = ET.SubElement(starttime, 'second')
  second.text = '00'

  for index, image in enumerate(images):
    # Make sure the last image transitions to the first.
    if index < len(images) - 1:
      next_image = images[index + 1]
    else :
      next_image = images[0]
    background.extend(
        _create_slideshow_xml_item_pair(image, next_image, duration_minutes))

  return ET.ElementTree(background)


def _create_slideshow_xml_item_pair(image, next_image, duration_minutes):
  """Creates a pair of ElementTree.Element objects to represent an image
  transition in the slideshow XML.

  Args:
    image: Local path to the wallpaper image.
    next_image: Local path to the following wallpaper image in the slideshow.
    duration_minutes: Duration in minutes for the `image` in this transition.

  Returns:
    A pair of ElementTree.Element (static, transition) that describe a
    transition between the two passed images in the slideshow.
  """

  # Reserve 5 sec for the change transition
  transition_duration_seconds = 5
  static_duration_seconds = ((duration_minutes * 60) -
      transition_duration_seconds)

  static = ET.Element('static')
  static_duration = ET.SubElement(static, 'duration')
  static_duration.text = str(static_duration_seconds)
  file = ET.SubElement(static, 'file')
  file.text = image

  transition = ET.Element('transition')
  transition_duration = ET.SubElement(transition, 'duration')
  transition_duration.text = str(transition_duration_seconds)
  from_image = ET.SubElement(transition, 'from')
  from_image.text = image
  to_image = ET.SubElement(transition, 'to')
  to_image.text = next_image

  return (static, transition)


def _create_background_properties_xml(album_name, slideshow_xml_filepath):
  """Creates an ElementTree that describes the contents of the background
  properties XML file for this wallpaper slideshow.

  Args:
    album_name: The name to be used in the Gnome wallpaper selector for this
        slideshow.
    slideshow_xml_filepath: Local path to the XML describing the slideshow
        image transitions.

  Returns:
    An ElementTree object with the contents of the background properties XML.
  """

  wallpapers = ET.Element('wallpapers')
  wallpaper = ET.SubElement(wallpapers, 'wallpaper')
  name = ET.SubElement(wallpaper, 'name')
  name.text = album_name
  filename = ET.SubElement(wallpaper, 'filename')
  filename.text = slideshow_xml_filepath
  options = ET.SubElement(wallpaper, 'options')
  options.text = 'zoom'
  pcolor = ET.SubElement(wallpaper, 'pcolor')
  pcolor.text = '#111111'
  scolor = ET.SubElement(wallpaper, 'scolor')
  scolor.text = '#111111'
  shade_type = ET.SubElement(wallpaper, 'shade_type')
  shade_type.text = 'solid'

  return ET.ElementTree(wallpapers)


if __name__ == '__main__':
  main()
