#!/usr/bin/perl
# ---------------------------------------------------------------------------
# Ruter2SDP.pl
#
# Generates Route data to feed into Dynamic Positioning system SDP10
#
# Usage: Ruter2SDP [--layer=1[,2,3..10]] file(s)...
#
# Input: Olex Ruter format
# Output: <STDOUT>
#
# ---------------------------------------------------------------------------
# By: A. Lagestrand, al@blom.no                      20(c)03 Blom Maritime AS
# ---------------------------------------------------------------------------





#----------------------------------------------
#Endret navn og datoprinting
#eivind.ervik@gmail.com
#
#
#
#
#
#
#----------------------------------------------
#
use File::Basename;
use Time::Local;
use Math::Trig;
use Math::Trig 'great_circle_direction';
use Math::Trig 'great_circle_distance';

# --  Variables  ------------------------------------------------------------
$script    = basename($0,".pl");

$rutetype  = "RUTE";
$lineno    = 0;
$DATUM     = "WGS84";	# always WGS84 in Olex Chart System

($file,@files) = ();
(@lat,@lon) = ();
@plottsett  = ();
my ($day, $month, $year, $dayofweek) = (localtime)[3,4,5,6];
$month = qw(January February March April May June July August September October November December )[$month];
$dayofweek = qw(Monday Tuesday Wednesday Thursday Friday Saturday Sunday)[$dayofweek];


# ---------------------------------------------------------------------------

&decodeArgs();

&msg("**  Reading Olex 'Ruter'  **");
&DPheader();

foreach $file (@files) {
  &msg("- reading $file...");
  open(RUTER,$file);

  while (<RUTER>) {
    $_ =~ s/(\s+)/ /g; chop();

    if (/^Rute (.*)/) {	# NEW LINE
      &flushdata($rutenavn,$rutetype) if ( &checkInArray($plottsett,@plottsett) );
      $lineno++;
      if (! $fast_rutenavn) {
        $rutenavn = sprintf("%s %d",$1,$lineno);
      } else {
        $rutenavn = sprintf("%s %d",$fast_rutenavn,$lineno);
      }
      (@lat,@lon,@navn) = ();
      next;
    }

    #if (/^Linjefarge (.*)$/) { $farge       = $1;     next; }	# linecolor
    if (/^Rutetype (.*)$/)   { $rutetype    = uc($1); next; }	# elementtype
    if (/^Plottsett (.*)$/)  { $plottsett   = $1;     next; }	# plotlayer
    if (/^Navn (.*)$/)       { $navn[$#lat] = "$1";   next; }	# waypoint name

    # DECODE COORDINATES
    if (/^(\d+\.?\d*) (\d+\.?\d*) (\d+) (.*)$/) { # lat,lon,time,symbol
    	$lat = $1 / 60;			# decimal degrees
    	$lon = $2 / 60;			# decimal degrees
	#print "## $lat - $lon\n";
	push @lat,$lat;
	push @lon,$lon;
    }
  }
  
  close RUTER;
}

# Flush last rutetype in file
if ( &checkInArray($plottsett,@plottsett) ){
  &flushdata($rutenavn,$rutetype);
}

&DPfooter;

exit 0;

# --  SUB ROUTINES  ---------------------------------------------------------

sub err { foreach (@_) { print STDERR "\n$_ \n\n"; } exit 1; }
sub msg {
  foreach (@_) {
    if ($_) {
      print STDERR "**  $_  **\n";
    } else {
      print STDERR "\n";
    }
  }
}

sub usage {
  print  STDERR "\nusage: $script [--layer=1[,2,3..10]] file(s)...\n\n";
  printf STDERR "    %s\n","This script takes an Olex 'Ruter' file, and generates";
  printf STDERR "    %s\n","an output for import into SDP 10 Dynamic Positioning System.";
  printf STDERR "    %s\n","All positions are WGS84 - latitude/longitude.\n\n";
  exit;
}

sub decodeArgs {
  my (@layers,$layer) = ();
  
  if (! @ARGV) { &msg("","Missing argument(s)"); usage(); }

  foreach (@ARGV){
	if (/^-h|--help$/) {
		&usage();
	} elsif (/^--layer=(.*)$/) {
		@layers = split(",|;",$1);
		foreach $layer (@layers){
		  $layer--;
		  push (@plottsett,2**$layer);
		}
	} elsif (/^Navn (.*)$/) {
		$fast_rutenavn = $1;
	} else {
		if (-f $_){ push (@files,$_); }	# input file
	}
  }
  
  if (! @files) { &err("No input file(s)...!"); }
}

sub flushdata {
  my $rutenavn	= shift;
  my $rutetype	= shift;
  my $i		= ();
  
  my @header = qw(Format Id HemisNS LatDeg LatMin HemisEW LonDeg LonMin LegType Head Speed TurnRad);
  my %element	= {};

 
  if (! @lat) { return; }			# empty element
  if ($#lat < 2) {				# single point
    &msg("Less than 2 positions in element (single point)","Not supported - skipped!");
    return;
  }
  if ($rutetype =~ /^AREAL$/) {			# closed polygon
    &msg("Areal not supported - element skipped!");
    return;
  }

  # write element header
  printf "TrackName,%s\n",basename($files[0], ".tmp");
  printf "NoOfWp,%d\n",   $#lat+1;
  printf "Datum,%s\n",    $DATUM;
  print  "WP$header[0]";
  foreach (1 .. $#header) { printf ",WP%s",$header[$_]; }
  print  "\n";
  
  
  foreach $i (0 .. $#lat) {
    $element{LegType} = 0;
    #$element{LegDist} = &calcDistance($lat[$i],$lon[$i],$lat[$i+1],$lon[$i+1]);
    #$element{Head}    = &calcBearing($lat[$i],$lon[$i],$lat[$i+1],$lon[$i+1]);
    $element{LegDist} = 0;
    $element{Head}    = 0;
    $element{Speed}   = 0;
    $element{TurnRad} = 0;
    
    printf "WP,%d,%s,%02d,%08.5f,%s,%02d,%08.5f",$i+1,&deg2min('LAT',$lat[$i]),&deg2min('LON',$lon[$i]); # ID + POSITION
    printf ",%d",$element{LegType};
    printf ",%.3f",$element{Head};
    printf ",%.4f",$element{Speed};
    printf ",%.2f",$element{TurnRad};
    print  "\n";
  }
}

sub calcDistance {
  my ($lat1,$lon1,$lat2,$lon2) = @_;
  my $rho = 6371;		# earth radius
  my $b = great_circle_distance(deg2rad($lon1),pi/2 - deg2rad($lat1),deg2rad($lon2),pi/2 - deg2rad($lat2), $rho);
  
  if ((! $lat2) and (! $lon2)) { return(); }
  return($b);
}

sub calcBearing {
  my ($lat1,$lon1,$lat2,$lon2) = @_;
  my $lat1 = deg2rad($_[0]);
  my $lon1 = deg2rad($_[1]);
  my $lat2 = deg2rad($_[2]);
  my $lon2 = deg2rad($_[3]);
  my $dlong = $lon2 - $lon1;
  my $b = atan2( sin($dlong)*cos($lat2) , cos($lat1)*sin($lat2) - sin($lat1)*cos($lat2)*cos($dlong) );
  #my $b = great_circle_direction($lon1,$lat1,$lon2,$lat2); # From Math::Trig - not working

  if ((! $lat2) and (! $lon2)) { return(); }
  if ($b < 0) {
    $b = rad2deg($b) + 360;
  } else {
    $b = rad2deg($b);
  }
  return($b);
}

sub deg2min {
  my $type = shift;
  my $deg  = int($_[0]);
  my $min  = ($_[0] - $deg) * 60;

  if ($type =~/^LAT$/){					# latitude
    if ($deg < 0){ $type = 'S'} else { $type = 'N'; }
  } elsif ($type =~/^LON$/) {				# longitude
    if ($deg < 0){ $type = 'W'} else { $type = 'E'; }
  }
  return($type,$deg,$min);
}

sub checkInArray {
  my $value = shift;
  if ( ! @_ ) { return(1); }
  foreach (@_){ if ( $value == $_ ) { return(1)}; }
  return(0);
}

sub DPfooter { print "END\n"; }
sub DPheader {
  my $Version = 4;
  my @time = localtime();
  printf "CreateDate,%s.%s%d.%04d-%02d:%02d\n",$dayofweek,$month,$day,$time[5]+1900,$time[2],$time[1];
  #printf "%04d-%02d:%02d\n",$time[5]+1900,$time[2],$time[1];
  printf "Version,%d\n",$Version;
}
