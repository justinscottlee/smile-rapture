import os
import sqlite3
import uuid

import subprocess
import secrets
import zipfile
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_unique_filename(filename):
    now = datetime.datetime.now()
    return filename + now.strftime("%Y%m%d%H%M%S")
