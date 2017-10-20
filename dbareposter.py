#!/usr/bin/python
import warnings
warnings.filterwarnings("ignore") # Ignoring warnings because fuzzywuzzy throws warning if using pure-python and not python-Levenshtein.
import sys
import os
import requests
from fuzzywuzzy import fuzz
import urllib.request
import json
import shutil

print("\n        =========================== \n       |        DBA Reposter       |\n       |   by Simon Klit-Johnson   |\n       |     blog.simonklit.com    |\n        =========================== \n")


class Listing:
   custom_id = None
   listing_id = None
   syi_id = None
   category = None
   matrixData = None
   additional_text = None
   price = None
   pictures = []

   def fill(self, l, iter):
      # Fill class with info from current listing
      self.custom_id = iter
      self.listing_id = l['ad-external-id']
      info = requests.get("https://api.dba.dk/api/v2/listing/%s/secondaryinfo" %
                          self.listing_id, headers=headers, verify=verify).json()
      self.category = int(l['classification']['id'])
      self.matrixData = l['matrixdata']
      if l['additional-text'] != "null":
         self.additional_text = l['additional-text']
      self.price = int(info['tracking']['gtm']['dataLayer']['a']['prc']['amt'])

      if len(l['pictures']) > 0:
         if not os.path.exists("images"):
            os.makedirs("images")
         self.images = []
         iter = 0
         for image in l['pictures'][2]['link']:
            iter = iter + 1
            if not os.path.exists("images/" + str(self.custom_id)):
               os.makedirs("images/" + str(self.custom_id))
            urllib.request.urlretrieve(
                image['href'], "images/" + str(self.custom_id) + "/" + str(iter) + ".jpg")
      return

   def create(self):
      syi_headers = {"X-Ad-Id": "7DC858CF-0522-40D3-9D5E-65EADF3983DE", 'dbaapikey': '2abb0a87-9e2f-4bdd-3d79-08d3e9335416',
          'User-Agent': 'dba/5.4.3 iPhone 10.0.1 (iPhone6,2)', 'Authorization': 'oauth ' + access_token, 'X-InstallationId': 'e9ad3824fd4d47c6b46e1e7bfc98c07b', 'X-Dba-AppVersion': '5.4.3.2'}
      create_headers = {"X-Ad-Id": "7DC858CF-0522-40D3-9D5E-65EADF3983DE", 'Content-Type': 'application/json', 'X-Ad-DFP-Impression-Counter': 0, 'Accept-Language': 'en-us', 'dbaapikey': '2abb0a87-9e2f-4bdd-3d79-08d3e9335416',
          'User-Agent': 'dba/5.4.3 iPhone 10.0.1 (iPhone6,2)', 'Authorization': 'oauth ' + access_token, 'X-InstallationId': 'e9ad3824fd4d47c6b46e1e7bfc98c07b', 'X-Dba-AppVersion': '5.4.3.2'}
      upload_headers = {'dbaapikey': '2abb0a87-9e2f-4bdd-3d79-08d3e9335416', 'Accept': 'application/json',
          'Content-Type': 'image/jpeg', 'User-Agent': 'dba/5.4.3 iPhone 10.0.1 (iPhone6,2)', 'Authorization': 'oauth ' + access_token}

      request = requests.put(
          "https://api.dba.dk/api/v2/syi/start", headers=headers, verify=verify).json()
      self.syi_id = request['syi']['syiId']
      request = requests.post("https://api.dba.dk/api/v2/syi/classification?format=json", data={
                              'syiId': self.syi_id, 'classificationId': self.category, 'listingType': -1}, headers=syi_headers, verify=verify).json()
      crafted_matrixData = []
      for group in self.matrixData:
         # match group['label'] with
         # request['syi']['matrixData']['matrixGroups'][n]['label'] with fuzzy
         # search:
         iterator = 0
         ratios = []
         for mGroup in request['syi']['matrixData']['matrixGroups']:
            ratios.append(fuzz.ratio(group['label'], request['syi'][
                          'matrixData']['matrixGroups'][iterator]['label']))
            iterator = iterator + 1

         maximum = int(ratios.index(max(ratios)))
         # print(request['syi']['matrixData']['matrixGroups'][minimum]['matrixElements'][0]['allowedValues'])
         # n = matched matrix group from above
         if max(ratios) >= 70:
             matrixGroup = {}
             if len(request['syi']['matrixData']['matrixGroups'][maximum]['matrixElements'][0]['allowedValues']) > 0:
                # match value from group['value'] with one of the allowedValues,
                # and get it's valueId
                for allowedValue in request['syi']['matrixData']['matrixGroups'][maximum]['matrixElements'][0]['allowedValues']:
                   if allowedValue['value'] == group['value']:
                      matrixGroup["valueId"] = allowedValue['valueId']

             matrixGroup["id"] = request['syi']['matrixData'][
                 'matrixGroups'][maximum]['matrixElements'][0]['id']
             matrixGroup["value"] = group['value']
             crafted_matrixData.append(matrixGroup)
      if os.path.exists("images/" + str(self.custom_id)):
         iter = 0
         for filename in os.listdir("images/" + str(self.custom_id)):
            iter = iter + 1
            if filename.endswith(".jpg"):
               with open("images/" + str(self.custom_id) + "/" + str(iter) + '.jpg', 'rb') as fh:
                  image = fh.read()
                  request = requests.post(
                      "https://api.dba.dk/api/v2/syi/pictures/upload/", headers=upload_headers, data=image, verify=verify).json()
               self.pictures.append(request["pictureIds"][0])
         request = requests.post("https://api.dba.dk/api/v2/syi/pictures/set/", headers=headers, json={'syiId': self.syi_id, 'pictures': self.pictures}, verify=verify).json()
      else:
         request = requests.post("https://api.dba.dk/api/v2/syi/pictures/set/", headers=headers, json={'syiId': self.syi_id, 'pictures': []}, verify=verify).json()
      user = requests.get("https://api.dba.dk/api/v2/user", headers=headers, verify=verify).json()
      profile = requests.get("https://api.dba.dk/api/v2/user/profile", headers=headers, verify=verify).json()

      craft = {
            "matrixData": crafted_matrixData,
            "paymentMethods": {
               "payPalEnabled": "false"
            },
            "questionAndAnswers": {
               "enabled": "true"
            },
            "contactInformation": {
               "email": user['email'],
               "showOnMap": "true",
               "zipCode": int(user['address']['zipCode']),
               "address": profile['summary']['address1']
            },
            "listingInfo": {},
            "price": {
               "price": str(int(self.price/100)),
               "hasValue": "false"
            },
            "runningSubscription": {
               "hasRunningSubscription": "false",
               "canRunningSubscriptionBeChanged": "false"
            },
            "bundlesAndProducts": {
               "productIds": [],
               "bundleTypeId": 4
            },
            "syiId": self.syi_id,
            "bundleTypeId": package,
            "listingType": {
               "selectedListingType": 2
            }
         }
      if self.additional_text != None:
         craft["listingInfo"] = {"additionalText":self.additional_text}

      request = requests.post("https://api.dba.dk/api/v2/syi/create/%s" % (self.syi_id), json=craft, headers=syi_headers, verify=verify).json()
      request = requests.post("https://api.dba.dk/api/v2/syi/publish/%s?format=json" % (self.syi_id), headers=syi_headers, verify=verify, data={"syiId": self.syi_id}).json()
      return

   def delete(self):
      request = requests.post("https://api.dba.dk/api/v2/ads/%s/delete/?sold=false" % self.listing_id, headers=headers, verify=verify).json()
      return

keep = 10
verify = True
package = 4

if len(sys.argv) <= 1:
   print("Usage: python %s username password [--keep=value] [--verify=value] [--premium=value] \n\tusername: Username/email for dba.dk\n\tpassword: Password for dba.dk\n\t--keep: Does not delete the original listing after repost.\n\t--verify: Whether or not to perform SSL verification.\n\t--premium: Whether or not to post new listings as premium listings." % (sys.argv[0]))
   sys.exit(0)
else:
    args = sys.argv[3:]
    for arg in args:
        argu = arg.split("=")[0]
        val = arg.split("=")[1]
        if argu == "--keep":
            keep = int(val)
        elif argu == "--verify":
            if(val.lower() == "true"):
                verify = True
                print("SSL verification set to %s." % str(verify).lower()) # Keep these prints here, as this should only print if the argument is set.
            else:
                verify = False
                print("SSL verification set to %s." % str(verify).lower()) # Keep these prints here, as this should only print if the argument is set.
        elif argu == "--premium":
            if(val.lower() == "true"):
                package = 3
            else:
                package = 4

print("Amount of days to keep listing alive set to %s." % (keep))
print("Package tier set to " + ('premium' if package == 3 else 'free') + ".")
print("\n")

if(os.stat("listings.json").st_size == 0):
   listings_file = {}
else:
  with open('listings.json') as data_file:    
    listings_file = json.load(data_file)

username = bytes(sys.argv[1], 'UTF-8')
password = bytes(sys.argv[2], 'UTF-8')

login_url = "https://api.dba.dk/api/v2/oauth/accesstoken"
login_headers = {'dbaapikey': '2abb0a87-9e2f-4bdd-3d79-08d3e9335416', 'User-Agent': 'dba/5.4.3 iPhone 10.0.1 (iPhone6,2)'}
r = requests.post(login_url, data={'username': username, 'password': password}, headers= login_headers, verify=verify).json()

if(r['success'] == True):
   logged_in = True
   access_token = r['access_token']
   refresh_token = r['refresh_token']
   headers = {'dbaapikey': '2abb0a87-9e2f-4bdd-3d79-08d3e9335416', 'Content-Type':'application/json', 'User-Agent': 'dba/5.4.3 iPhone 10.0.1 (iPhone6,2)', 'Authorization': 'oauth ' + access_token}
   print("Logged in as: " + requests.get("https://api.dba.dk/api/v2/user/profile", headers=headers, verify=verify).json()['summary']['display-name'])
else:
   print("Incorrect credentials. Exiting script.")
   logged_in = False
   sys.exit(0)

# Get ads/listings
ads_url = "https://api.dba.dk/api/v2/ads/user"
r = requests.get(ads_url, headers=headers, verify=verify).json()
amount_of_listings = len(r)

for listing in r:
   comments = requests.get("https://api.dba.dk/api/v2/ads/%s/posts" % (listing["ad-external-id"]), headers=headers, verify=verify).json()
   if (listing['ad-status']['status-id'] == 2) or (len(comments) > 0):
      amount_of_listings -= 1

if amount_of_listings == 0:
   print("Amount of active listings with no comments: 0. Exiting script.")
   sys.exit(0)
else:

   print("Amount of active listings with no comments: %s.\n" % (amount_of_listings))
   print("Running listings.")
   iter = 0
   for l in r:
      comments = requests.get("https://api.dba.dk/api/v2/ads/%s/posts" % (l["ad-external-id"]), headers=headers, verify=verify).json()
      if (l['ad-status']['status-id'] == 2) or (len(comments) > 0):
         continue
      else:
         iter = iter + 1
         print("Running listing %s." % (iter))
         listing = Listing()
         listing.fill(l, iter)
         if listing.listing_id in listings_file:
          listing_count = listings_file[listing.listing_id]
          listing_count = listing_count + 1
          listings_file[listing.listing_id] = listing_count
          if int(listings_file[listing.listing_id]) >= keep:
            listing.delete()
            del listings_file[listing.listing_id]
            print("Listing %s deleted after it was kept for %s runs." % (iter, keep))
         else:
          listing.create()
          listings_file[listing.listing_id] = 1
          print("Listing %s reposted." % (iter))
          if int(listings_file[listing.listing_id]) >= keep:
            listing.delete()
            del listings_file[listing.listing_id]
            print("Listing %s deleted after it was kept for %s runs." % (iter, keep))
         print(" ")

if os.path.exists("images"):
    shutil.rmtree('images')

with open('listings.json', 'w') as outfile:
    json.dump(listings_file, outfile)

print("\nListings succesfully reposted. Exiting script.")
sys.exit(0)
