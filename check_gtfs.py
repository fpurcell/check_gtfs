import os
import shutil
import sys
import csv
import re
import urllib2
import filecmp
import shutil
import zipfile
import datetime
import logging
import traceback

class TestCalendarDate():
    """ Test's GTFS calendar_date.txt file to see if it's older than existing GTFS version...
    """

    def __init__(self, existing_gtfs_path=None, gtfs_url=None):
        """
        """
        self.tmp_dir      = "./tmp"
        self.new_gtfs_zip = "gtfs.zip"
        self.old_gtfs_zip = "/home/otp/OtpDeployer/otp/cache/gtfs/gtfs.zip"
        self.gtfs_url     = "http://developer1.trimet.org/schedule/gtfs.zip"
        
        if existing_gtfs_path is not None:
            self.old_gtfs_zip = existing_gtfs_path
        if gtfs_url is not None:
            self.gtfs_url = gtfs_url


    def download_gtfs(self, url=None, zip=None):
        """ grab gtfs.zip file from url
            IMPORTANT NOTE: this will *not* work if the URL is a redirect, etc...
        """
        if url is None:
            url = self.gtfs_url
        if zip is None:
            zip = self.new_gtfs_zip
        
        try:
            # get gtfs file from url
            req = urllib2.Request(url)
            res = urllib2.urlopen(req)

            # write it out
            f = open(zip, 'w')
            f.write(res.read())
            f.flush()
            f.close()
            res.close()
            
            logging.info("check_gtfs: downloaded " + url + " into file " + zip)
        except:
            logging.warn('ERROR: could not get data from url:\n', url, '\n(not a friendly place)')
            traceback.print_exc(file=sys.stdout)
            pass


    def unzip_file(self, zip_file, target_file, file_name='calendar_dates.txt'):
        """ unzips a file from a zip file...
            @returns True if there's a problem...
        """
        ret_val = False
        try:
            zip  = zipfile.ZipFile(zip_file, 'r')
            file = open(target_file, 'w')
            file.write(zip.read(file_name))
            file.flush()
            file.close()
            zip.close()
        except:
            ret_val = False
            logging.warn("ERROR: problems extracting " + file_name + " from " + zip_file + " into file " + target_file)
            traceback.print_exc(file=sys.stdout)

        return ret_val

    def unzip_calendar_dates(self, cal_file='calendar_dates.txt'):
        """ unzip a file (calendar_dates.txt by default) from our old & new gtfs.zip files
        """
        # step 1: unzip the cal_file from the old gtfs file
        old_name = "old_" + cal_file
        self.unzip_file(self.old_gtfs_zip, old_name, cal_file)

        # step 2: unzip the cal_file from the old gtfs file
        new_name = "new_" + cal_file
        self.unzip_file(self.new_gtfs_zip, new_name, cal_file)
        return old_name, new_name


    def cmp_calendar_dates(self, old_name, new_name):
        """ return whether files are the same or not...
        """
        ret_val = False
        try:
            ret_val = filecmp.cmp(old_name, new_name)
            logging.info(old_name + " is the same as " + new_name + ": " + str(ret_val))
        except:
            ret_val = False
            logging.warn("ERROR: problems comparing " + old_name + " and " + new_name)
            traceback.print_exc(file=sys.stdout)
        return ret_val


    def get_date_range_of_calendar_dates(self, file_name):
        """ date range of new gtfs file
        """
        start_date = 'ZZZ'
        end_date = ''
        today = datetime.datetime.now().strftime("%Y%m%d")
        today_position = -111
        total_positions = 0

        file = open(file_name, 'r')
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            date = row['date']
            if date < start_date:
                start_date = date
            if date > end_date:
                end_date = date
            if date == today:
                today_position = i
            total_positions = i

        # give total positions some value
        if today_position < 0:
            today_position = total_positions

        logging.info(" date range of file " + file_name + ": " + start_date + " to " + end_date +
                     ", and today " + today + " position is " + str(today_position) + " of " + str(total_positions))
        return start_date, end_date, today_position, total_positions


    def gtfs_calendar_age(self, gtfs):
        """ calculate the number of days since the gtfs was generated, and number of days left within the calendar
        """
        start_date,end_date,pos,total=self.get_date_range_of_calendar_dates(gtfs)
        sdate = datetime.datetime.strptime(start_date, '%Y%m%d')
        edate = datetime.datetime.strptime(end_date, '%Y%m%d')
        sdiff = datetime.datetime.now() - sdate
        ediff = edate - datetime.datetime.now()
        logging.info("first - {0} was {1} days ago".format(start_date, sdiff.days))
        logging.info("last  - {0} is  {1} days after today".format(end_date, ediff.days))
        return sdiff.days, ediff.days
        
        
    def is_gtfs_out_of_date(self, gtfs):
        """ calculate whether we think gtfs is out of date
        """
        ret_val = False
        start_date,end_date,pos,total=self.get_date_range_of_calendar_dates(gtfs)
        pos_diff=pos * 1.0001 / total        

        sdays, edays = self.gtfs_calendar_age(gtfs)
        if pos_diff > 0.40 or sdays > 30 or edays < 30:
            ret_val = True
        return ret_val


    def mk_tmp_dir(self):
        """ remove existing ./tmp directory, and make new / empty one
        """
        shutil.rmtree(self.tmp_dir, True)
        if not os.path.exists(self.tmp_dir):        
            os.makedirs(self.tmp_dir)

    def cd_tmp_dir(self):
        """ make a ./tmp directory, and cd into it...
        """
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)
        os.chdir(self.tmp_dir)


    def update_gtfs(self):
        """ backup old gtfs file, and move new gtfs file into graph cache...
        """
        if os.path.isfile(self.old_gtfs_zip):
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            shutil.copy2(self.old_gtfs_zip, self.old_gtfs_zip + today)
        if os.path.isfile(self.new_gtfs_zip):
            shutil.copy2(self.new_gtfs_zip, self.old_gtfs_zip)


def main():
    logging.basicConfig(level=logging.INFO)
    tcd = TestCalendarDate()
    tcd.cd_tmp_dir()
    tcd.download_gtfs()
    old_name, new_name = tcd.unzip_calendar_dates()
    is_same_gtfs=tcd.cmp_calendar_dates(old_name, new_name)
    start_date,end_date,pos,total=tcd.get_date_range_of_calendar_dates(new_name)
    
if __name__ == '__main__':
    main()
