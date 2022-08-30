# FileWave & AutoPkg
These recipes allow FileWave admins to import applications as filesets 
or pkgs into FileWave, ready for deployment to test machines. 

Our aim was to avoid replicating existing recipes as much as possible, as such most of the
recipes will use a parent recipe that is already part of the standard autopkg repo.

## Pre-requisites
The following is *required* in order to use these recipes: 

1. On the machine that runs autopkg you must have a copy of FileWave Admin 10.0
or greater installed.
1. AutoPkg 0.5.0 or greater.

The FileWave autopkg recipes rely on having access to the FileWave Admin 
Command Line features which are part of the FileWave Admin application.

You can confirm that you have the right version by running the FileWave Admin
Command Line from the Terminal, for example:

    $ /Applications/FileWave/FileWave\ Admin.app/Contents/MacOS/FileWave\ Admin -v
    10.0.0
    $

## Configuration
The recipes and processors need to know where the FileWave Server is located, as well
as which user / password to use when logging in and uploading packages.
  
To do this, the following autopkg (defaults command) variables can be used:

1. FW_SERVER_HOST - defaults to 'localhost', can be hostname or IP address
1. FW_SERVER_PORT - defaults to 20016
1. FW_ADMIN_USER - defaults to 'fwadmin', its the name of the account that will be used to connect
1. FW_ADMIN_PASSWORD - defaults to 'filewave', its the password of the FW_ADMIN_USER account

For example:

	defaults write com.github.autopkg FW_SERVER_HOST 10.3.4.5

## Security
By default the recipes will assume you have a pristine FileWave installation 
which means you have a single FileWave administrator account called 'fwadmin'
and the password is 'password'.  These are good defaults to ensure a quick 
start in testing situations - but in production you *really really* want to 
change this.

For security reasons - we *strongly* recommend creating another user 
for use with AutoPkg.  

If you insist on using the fwadmin user - you will see annoying warnings 
indicating that you are making use of the super-user account.
   
## FW_ADMIN_USER Permissions
FileWave is multi-user capable.  

Take advantage of this and create a user called 'autopkg' and give this 
user the following rights (optionally provide update model rights if you want to make
use of the --updateModel feature of the Admin CLI): 
 - Modify Clients/Groups
 - Modify Filesets
 - Modify Associations
 - Modify Imaging Associations
 - [optional] Update Model
  
Then on the machine running autopkg, set the FW_ADMIN_USER value:

    defaults write com.github.autopkg FW_ADMIN_USER autopkg

To enable model update on an override add:
    
    <key>fw_model_update</key>
    <true/>
    
# Validation of the setup
In order to quickly validate whether or not your setup is working you can run
a dummy recipe that will invoke the FileWave command line tools to print out 
relevant version information.  

This simple test proves that the autopkg scripts and FileWave magic sauce 
are working well together. 

For example (assuming that you've set the FW_ADMIN_USER to autopkg):

    $ autopkg run FWTool.filewave
    Path to Admin Tool: /Applications/FileWave/FileWave Admin.app/Contents/MacOS/FileWave Admin

    Here are the results of installation validation:
    Fw Admin Console Version  Fw Admin User  Fw Server Host  Fw Server Port  Fw Can List Filesets  Fw Message     
    ------------------------  -------------  --------------  --------------  --------------------  ----------     
    10.0.0                    autopkg        localhost       20016           Yes                   VALIDATION OK  


# Override Fileset Group
By default, the autopkg system will put newly created filesets into the root group.

You can override this behaviour in two ways: 
 1. Specify a default group for *all* of the imports from autopkg
 2. Use autopkg's make-override verb to override the *fw_fileset_group* parameter value for a specific recipe.

The first option is a great choice if you want all of your imports to go into a single folder, and it
carries the added advantage that you don't need to modify the recipes as long as the recipe DOES NOT specify
the fw_fileset_group witin the Input section of the recipe.

If the recipe specifies an empty fw_fileset_group value in its Input section, this is redundant and can be removed.

Here's how to set the default Fileset group into which autopkg will place newly imported packages: 
  
    $ defaults write com.github.autopkg fw_fileset_group "My_New_Autopkg_Group"

The second way to override the default group is to create a recipe override.  Recipe overrides are explained in 
the autopkg documentation in more detail.  Lets follow an example of making an override for Adium.

Recipe overrides are created using the autopkg command line tool.  The intention is to provide you a way
to override the values in the input section of a recipe.  *Important*: the input variable does not have to 
exist in the recipe in order for you to override it - and we'll use this trick to our advantage.

First, lets see what info we've got about the Adium recipe.

    $ autopkg info Adium.filewave
    Description:         Downloads latest version of Adium and imports into FileWave.
    Identifier:          com.github.autopkg.filewave.Adium
    Munki import recipe: False
    Has check phase:     True
    Builds package:      False
    Recipe file path:    /Users/johnc/Library/AutoPkg/RecipeRepos/com.github.filewave/Adium/Adium.filewave.recipe
    Parent recipe(s):    /Users/johnc/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes/Adium/Adium.download.recipe
    Input values: 
 
    BRANCH = release;
    NAME = Adium;
    "fw_app_bundle_id" = "com.github.autopkg.filewave.Adium";
    "fw_destination_root" = "/Applications/%NAME%.app";


Note the *Input values* section, it shows us BRANCH, NAME and two filewave specific parameters. Notice the 
'fw_fileset_group' parameter is NOT listed here.  

Lets go ahead and create an override and then set the fw_fileset_group paramter to something.

    $ autopkg make-override Evernote.filewave
    Override file saved to /Users/johnc/Library/AutoPkg/RecipeOverrides/Adium.filewave.recipe
    
Now lets edit this XML file and make it look like this: 
```
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
        <key>Identifier</key>
        <string>local.filewave.Adium</string>
        <key>Input</key>
        <dict>
                <key>BRANCH</key>
                <string>release</string>
                <key>NAME</key>
                <string>Adium</string>
                <key>fw_app_bundle_id</key>
                <string>com.github.autopkg.filewave.Adium</string>
                <key>fw_destination_root</key>
                <string>/Applications/%NAME%.app</string>
                <!-- added the fw_fileset_group -->
                <key>fw_fileset_group</key>
                <string>My New Group for Adium</string>
        </dict>
        <key>ParentRecipe</key>
        <string>com.github.autopkg.filewave.Adium</string>
</dict>
</plist>
```

Notice that we've added the <key>fw_fileset_group</key> and its associated <string> value
into the input variables dictionary.  It isn't important that this key is not specified by the
original recipe - the FileWaveImporter will still look for and find the value you specify.

That's it!  Now when we run the autopkg recipe for Adium, the right group override is used.

    $ autopkg run Adium.filewave
    Processing Adium.filewave...

    The following fileset was imported:
    Fw Fileset Id  Fw Fileset Group        Fw Fileset Name   
    -------------  ----------------        ---------------   
    73533          My New Group for Adium  Adium - 1.5.10.2  

Happy Autopkging!

