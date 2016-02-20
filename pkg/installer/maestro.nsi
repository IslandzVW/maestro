;;
;; In order to successfully build this installer you need to have
;; the following NSIS plugins also installed.
;;
;;      NSIS_Simple_Service_PLugin
;;      UserMgr
;;      Blowfish
;;

!define PRODUCT_NAME "InWorldz Maestro"
!define PRODUCT_VERSION "1.0"
!define PRODUCT_FULLNAME "${PRODUCT_NAME} ${PRODUCT_VERSION}"
!define PRODUCT_DESCRIPTION "InWorldz Maestro Server Manager"
!define PRODUCT_PUBLISHER "InWorldz"
!define PRODUCT_WEB_SITE "http://www.inworldz.com"

; Where are the files to be packaged
!define PRODUCT_SRCDIR "..\..\dist"

; Password we use to encrypt the user password in the registry
!define PRODUCT_SERVICE_PASSWORD_KEY "codfish"

; Additional Settings
!define PRODUCT_LICENSE "LICENSE"
!define PRODUCT_ICON "maestro.ico"
!define PRODUCT_EXE "maestro.exe"
!define PRODUCT_SERVICENAME "InWorldz.Maestro"
!define PRODUCT_UNINSTALLER "uninstall.exe"
!define PRODUCT_STARTMENU "$SMPROGRAMS\${PRODUCT_FULLNAME}"

; Registry settings
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\${PRODUCT_EXE}"
!define PRODUCT_DIR_ROOT_KEY "HKLM"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_FULLNAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

;--------------------------------
;General

Name "${PRODUCT_FULLNAME}"
Caption "${PRODUCT_FULLNAME}"
OutFile "${PRODUCT_FULLNAME}-Setup.exe"

!ifdef PRODUCT_ICON
Icon "${PRODUCT_ICON}"
!endif

SetDateSave on
SetDatablockOptimize on
CRCCheck on
SilentInstall normal
ShowInstDetails hide
ShowUnInstDetails hide
RequestExecutionLevel admin
ManifestSupportedOS Win8

InstallDir "$PROGRAMFILES64\${PRODUCT_FULLNAME}"
InstallDirRegKey "${PRODUCT_DIR_ROOT_KEY}" "${PRODUCT_DIR_REGKEY}" ""

!ifdef PRODUCT_LICENSE"
LicenseText "License"
LicenseData "${PRODUCT_LICENSE}"
!endif

; MUI2 Definitions
!define MUI_ABORTWARNING
!define MUI_ICON "maestro.ico"
!define MUI_UNICON "maestro.ico"

; MUI 1.67 compatible ------
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "MUI2.nsh"

; Variables
; -------------------------------------------------
Var Dialog
Var Label
Var ServiceUsername_Label
Var ServicePassword_Label
Var SERVICE_USERNAME
Var SERVICE_PASSWORD
Var DOMAIN_PART
Var USER_PART

;--------------------------------
; Macros

;--------------------------------------------------------
; Setting up a macro for the IndexOf string function
;--------------------------------------------------------
!macro IndexOf Var Str Char
    Push "${Char}"
    Push "${Str}"
    Call IndexOf
    Pop "${Var}"
!macroend

!define IndexOf "!insertmacro IndexOf"

;--------------------------------------------------------
; Setting up a macro for the IndexOf string function
;--------------------------------------------------------

!macro GetUserPart Var UserName
    ; cut up the full username
    ${IndexOf} "${UserName} "\"
    StrCmp $R0 "-1" done
    $StrCpy $DOMAIN_PART "${UserName}" $R0
    IntOp $R0 $R0 + 1
    $StrCpy $USER_PART "${UserName}" "" $R0
!macroend

;--------------------------------
; Functions

Function .onInit

  ;; Did they pass us username and password on the command line?
  Push $R0
  Push $R1
  Push $R2
  ${GetParameters} $R0
  ${GetOptions} $R0 "/username=" $R1
  ${GetOptions} $R0 "/password=" $R2
  StrCpy $SERVICE_USERNAME $R1
  StrCpy $SERVICE_PASSWORD $R2
  Pop $R2
  Pop $R1
  Pop $R0

  StrCmp $SERVICE_USERNAME "" GetUserNameFromRegistry StartInstall
  
  ; If we were run before these should exist
  GetUserNameFromRegistry:
    ReadRegStr $SERVICE_USERNAME HKLM "SOFTWARE\${PRODUCT_FULLNAME}" "ServiceUserName"
    ReadRegStr $SERVICE_PASSWORD HKLM "SOFTWARE\${PRODUCT_FULLNAME}" "ServicePassword"
    
    StrLen $0 $SERVICE_PASSWORD
    IntCmp $0 0 NoDecrypt
    blowfish::decrypt $SERVICE_PASSWORD "${PRODUCT_SERVICE_PASSWORD_KEY}"
    StrCpy $SERVICE_PASSWORD $8
            
  NoDecrypt:
    StrCmp $SERVICE_USERNAME "" GetUserName StartInstall
        
  ; Get the current user and domain name and use that if needed.
  GetUserName:
    UserMgr::GetCurrentUserName
    Pop $USER_PART
    UserMgr::GetCurrentDomain
    Pop $DOMAIN_PART
    StrCpy $SERVICE_USERNAME "$DOMAIN_PART\$USER_PART"
  
  StartInstall:
  
FunctionEnd

Function InstallService

  ; Install the Service 
  DetailPrint "Installing Maestro Service"
  SimpleSC::InstallService "${PRODUCT_SERVICENAME}" "${PRODUCT_FULLNAME}" "16" "2" "$INSTDIR\maestro_service.exe" "" "$SERVICE_USERNAME" "$SERVICE_PASSWORD"
  Pop $0 ; returns an errorcode (<>0) otherwise success (0)
  ${If} $0 <> 0
      Push $0
      SimpleSC::GetErrorMessage
      Pop $0
      MessageBox MB_OK|MB_ICONSTOP "Cannot install Service ${PRODUCT_SERVICENAME} - Reason: $0"
  ${Else}  
      ; Grant the service logon privilege to "MyServiceUser"
      DetailPrint "Granting ServiceLogonPrivilege to $SERVICE_USERNAME"
      SimpleSC::GrantServiceLogonPrivilege "$SERVICE_USERNAME"
      Pop $0 ; returns an errorcode (<>0) otherwise success (0)
      ${If} $0 <> 0
        Push $0
        SimpleSC::GetErrorMessage
        Pop $0
        MessageBox MB_OK|MB_ICONSTOP "Cannot grant service login priviledge for ${PRODUCT_SERVICENAME} - Reason: $0"
      ${EndIf} 
      ; Start the Service
      DetailPrint "Starting the Maestro Service"
      SimpleSC::StartService "${PRODUCT_SERVICENAME}" "" "60"
      Pop $0
      ${If} $0 <> 0
        Push $0
        SimpleSC::GetErrorMessage
        Pop $0
        MessageBox MB_OK|MB_ICONSTOP "Unable to start ${PRODUCT_SERVICENAME} service - Reason: $0"
      ${EndIf} 
  ${EndIf}

FunctionEnd

Function RemoveService

  ; Check if the service exists
  SimpleSC::ExistsService "${PRODUCT_SERVICENAME}"
  Pop $0 ; returns an errorcode if the service doesn´t exists (<>0)/service exists (0)
  ${If} $0 == 0
    ; Check if the service is running
    SimpleSC::ServiceIsRunning "${PRODUCT_SERVICENAME}"
    Pop $0 ; returns an errorcode (<>0) otherwise success (0)
    Pop $1 ; returns 1 (service is running) - returns 0 (service is not running)
    ${If} $1 == 1
      SimpleSC::StopService "${PRODUCT_SERVICENAME}" "1" "60"
      Pop $0 ; returns an errorcode (<>0) otherwise success (0)
    ${EndIf}
    SimpleSC::RemoveService "${PRODUCT_SERVICENAME}"
    Pop $0  
  ${EndIf}
  
FunctionEnd

Function nsDialogsPage

  nsDialogs::Create 1018
  Pop $Dialog
  
  ${If} $Dialog == error
    Abort
  ${EndIf}
  
  ${NSD_CreateLabel} 0 0 100% 12u "Service Domain\Username:"
  Pop $Label
  ${NSD_CreateText} 0 13u 100% 12u $SERVICE_USERNAME
  Pop $ServiceUsername_Label
  
  ${NSD_CreateLabel} 0 30u 100% 12u "Service Password:"
  Pop $Label
  ${NSD_CreateText} 0 43u 100% 12u $SERVICE_PASSWORD
  Pop $ServicePassword_Label

  nsDialogs::Show
  
FunctionEnd

Function nsDialogsPageLeave

  ${NSD_GetText} $ServiceUsername_Label $SERVICE_USERNAME
  ${NSD_GetText} $ServicePassword_Label $SERVICE_PASSWORD

FunctionEnd

Function un.onUninstSuccess

  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."

FunctionEnd

Function un.onInit

  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2
  Abort

FunctionEnd


; PAGES
; -------------------------------------------------

; License Page
!ifdef PRODUCT_LICENSE
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!endif

; Get the installation directory
!insertmacro MUI_PAGE_DIRECTORY

; Get account name and password
Page custom nsDialogsPage nsDialogsPageLeave

; Install files
!insertmacro MUI_PAGE_INSTFILES

; Finish Up
!insertmacro MUI_PAGE_FINISH

; Confirm Uninstall
!insertmacro MUI_UNPAGE_CONFIRM

; Uninstall Files
!insertmacro MUI_UNPAGE_INSTFILES

;Languages
!insertmacro MUI_LANGUAGE "English"

AutoCloseWindow false

;--------------------------------
; Sections

Section "InWorldz Maestro Application" Install

  ; If the service is already installed remove it
  Call RemoveService
    
  ;Store installation folder
  WriteRegStr HKCU "Software\${PRODUCT_FULLNAME}" "" $INSTDIR
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\${PRODUCT_EXE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "${PRODUCT_UNINSTALLER}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\${PRODUCT_ICON}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  
  SetOverwrite try
  SetOutPath "$INSTDIR"
  
  !ifdef PRODUCT_LICENSE
  File "${PRODUCT_LICENSE}"
  !endif
  
  ; Maestro Files
  File "${PRODUCT_SRCDIR}\*.dll"
  File "${PRODUCT_SRCDIR}\*.exe"
  ;File "${PRODUCT_SRCDIR}\*.zip"
  File /r "${PRODUCT_SRCDIR}\lib"
  
  ; PsExec
  File "PsExec.exe"
  
  ; Uninstaller
  WriteUninstaller "$INSTDIR\${PRODUCT_UNINSTALLER}"
  
  ; AppData - C:\Users\inworldzgrid\AppData\Roaming
  CreateDirectory "C:\Users\$USER_PART\AppData\Roaming\${PRODUCT_FULLNAME}"
  SetOutPath "C:\Users\$USER_PART\AppData\Roaming\${PRODUCT_FULLNAME}"
  
  File /r "${PRODUCT_SRCDIR}\data\*"
  
  ; ShortCuts
  !ifdef PRODUCT_STARTMENU
  CreateDirectory "${PRODUCT_STARTMENU}"
  SetOutPath "${PRODUCT_STARTMENU}"
  CreateShortcut "${PRODUCT_STARTMENU}\Uninstaller.lnk" "$INSTDIR\${PRODUCT_UNINSTALLER}"
  CreateShortcut "${PRODUCT_STARTMENU}\Remote Console.lnk" "$INSTDIR\remote_console.exe"
  CreateShortcut "${PRODUCT_STARTMENU}\Maestro Configuration.lnk" "$APPDATA\${PRODUCT_FULLNAME}\maestro.config"
  !endif
  
  ; Encrypt and stash the password and username
  DetailPrint "Setting ServiceUserName registry entry to $SERVICE_USERNAME"
  WriteRegStr HKLM "SOFTWARE\${PRODUCT_FULLNAME}" "ServiceUserName" "$SERVICE_USERNAME"
  StrLen $0 $SERVICE_PASSWORD
  IntCmp $0 0 NoEncrypt
    blowfish::encrypt $SERVICE_PASSWORD "${PRODUCT_SERVICE_PASSWORD_KEY}"
    DetailPrint "Setting ServicePassword registry entry to $8"
    WriteRegStr HKLM "SOFTWARE\${PRODUCT_FULLNAME}" "ServicePassword" "$8"
    Goto PassRegSet
    
  NoEncrypt:
    DetailPrint "Clearing ServicePassword registry entry"
    WriteRegStr HKLM "SOFTWARE\${PRODUCT_FULLNAME}" "ServicePassword" ""
    
  PassRegSet:
    
  ; Install and Start the Service
  DetailPrint "Installing and Starting Maestro Service"
  Call InstallService
  
SectionEnd

Section "Uninstall" Uninstall

  ; Install and Start the Service
  DetailPrint "Stopping and removing existing Maestro Service (if installed)"
  ; If the service is already installed remove it
  ; Check if the service exists
  SimpleSC::ExistsService "${PRODUCT_SERVICENAME}"
  Pop $0 ; returns an errorcode if the service doesn´t exists (<>0)/service exists (0)
  ${If} $0 == 0
    ; Check if the service is running
    SimpleSC::ServiceIsRunning "${PRODUCT_SERVICENAME}"
    Pop $0 ; returns an errorcode (<>0) otherwise success (0)
    Pop $1 ; returns 1 (service is running) - returns 0 (service is not running)
    ${If} $1 == 1
      SimpleSC::StopService "${PRODUCT_SERVICENAME}" "1" "60"
      Pop $0 ; returns an errorcode (<>0) otherwise success (0)
    ${EndIf}
    SimpleSC::RemoveService "${PRODUCT_SERVICENAME}"
    Pop $0  
  ${EndIf}
  
  DetailPrint "Cleaning up Registry"
  DeleteRegKey /ifempty HKCU "Software\${PRODUCT_FULLNAME}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    
  !ifdef PRODUCT_STARTMENU
  DetailPrint "Removing StartMenu entries"
  Delete "${PRODUCT_STARTMENU}\Uninstaller.lnk"
  Delete "${PRODUCT_STARTMENU}\Remote Console.lnk"
  Delete "${PRODUCT_STARTMENU}\Maestro Configuration.lnk" 
  RMDir "${PRODUCT_STARTMENU}"
  !endif
  
  ; Remove the installed application directory
  DetailPrint "Removing Product Binaries"
  RMDir /r $INSTDIR\lib
  RMDir /r $INSTDIR

SectionEnd