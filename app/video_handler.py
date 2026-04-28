'''
This module handles the YouTube video operations
'''

import logging

logging.basicConfig(level=logging.DEBUG)

def url_input():
    """
    This function takes the URL input
    :return: url
    """
    url = input("Enter YouTube URL: ")
    return url

