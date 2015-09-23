# FileWave & AutoPkg
These recipes allow FileWave admins to
import applications as filesets or pkgs into FileWave, ready for deployment to
test machines. 

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

## Quickstart
If you don't want to read all the details below - setup autopkg as follows:

	1. Create a new FileWave admin account, call it 'autopkg'
	2. On the machine where you want to run AutoPKG do this:
		defaults write com.github.autopkg FW_SERVER_HOST <your-fw-server-ip-here>
		defaults write com.github.autopkg FW_ADMIN_USER autopkg
		defaults write com.github.autopkg FW_ADMIN_USER <autopkg-user-password-here>
	3. Check that the setup is working by running the validation, for example (assuming 
	   that you've set the FW_ADMIN_USER to autopkg as instructed above):

    $ autopkg run FWTool.filewave
    Path to Admin Tool: /Applications/FileWave/FileWave Admin.app/Contents/MacOS/FileWave Admin

    Here are the results of installation validation:
    Fw Admin Console Version  Fw Admin User  Fw Server Host  Fw Server Port  Fw Can List Filesets  Fw Message
    ------------------------  -------------  --------------  --------------  --------------------  ----------
    10.0.0                    autopkg        localhost       20016           Yes                   VALIDATION OK

## Required Configuration
The recipes and processors need to know where the FileWave Server is located, as well
as which user / password combo to use when uploading packages.
  
To do this, the following variables can be used:

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
start in testing situations - but in production you really really want to 
change this.

For security reasons - we *strongly* recommend creating another user 
for use with AutoPkg.  

If you insist on using the fwadmin user - you will see annoying warnings 
indicating that you are making use of the super-user account.
   
## FW_ADMIN_USER Permissions
FileWave is multi-user capable.  

Take advantage of this and create a user called 'autopkg' and give this 
user the following rights (DO NOT provide update model rights): 
 - Modify Clients/Groups
 - Modify Filesets
 - Modify Associations
 - Modify Imaging Associations
  
Then on the machine running autopkg, set the FW_ADMIN_USER value:

    defaults write com.github.autopkg FW_ADMIN_USER autopkg
    
# Validating Setup 
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


    
    
    

