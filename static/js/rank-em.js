
$(document).ready(function() {
  // Setup the drag-and-drop ranking table:
  $("#ranking-table").tableDnD({
    onDragStart: clearTeamInfoBox,
    onDragClass: "drag-row",
    onDrop: function(table, row) {
      $(row).addClass('moved');
      adjustRankAndRowColor(true, false);
    }
  });
  // Setup the editable export list:
  $('#export-list').on('change', sortByExportList);
});

function sortByExportList() { 
  var ranks = $('#export-list').val().split('\n');
  var validRanks = true; // Until we prove otherwise
  
  var sum = 0;
  if (ranks.length != 32) {
    validRanks = false;
  } else {
    var values = [];
    for (var i = 0; i < ranks.length; i++) {
      rank = $.trim(ranks[i]);
      if ($.isNumeric(rank) && // It's a number
          Math.floor(parseFloat(rank)) == parseFloat(rank) && // It's an integer
          $.inArray(rank, values) == -1 // It's a unique value
      ) { 
        sum += parseInt(rank);
        values.push(rank);
      } else {
        validRanks = false;
        break;
      }
    }
  }
  if (validRanks && sum == 528) { // 1 + 2 + 3 + ... + 31 + 32 = 528
    $('#ranking-table').each(function() {
      var rows = $('tbody > tr:not(:first-child)', this);
      rows.sort(function(a, b) {
        // Sort by team nickname:
        var fullnameA = $('td:eq(3)', a).text();
        var fullnameB = $('td:eq(3)', b).text();
        var nicknameA = fullnameA.substring(fullnameA.lastIndexOf(' '), fullnameA.length);
        var nicknameB = fullnameB.substring(fullnameB.lastIndexOf(' '), fullnameB.length);
        if (nicknameA < nicknameB) return -1;
        if (nicknameA > nicknameB) return 1;

        return 0;
      });
      // Map each team's nickname to their export list ranking:
      var name_rank_mapping = {};
      $.each(rows, function(index, row) {
        name_rank_mapping[$('td:eq(3)', row).text()] = parseInt(ranks[index]);
      });
      rows.sort(function(a, b) {
        // Sort again, this time by export list ranking:
        var nameA = $('td:eq(3)', a).text();
        var nameB = $('td:eq(3)', b).text();
        if (name_rank_mapping[nameA] < name_rank_mapping[nameB]) return -1;
        if (name_rank_mapping[nameA] > name_rank_mapping[nameB]) return 1;

        return 0;
      });
      $.each(rows, function(index, row) {
        $('#ranking-table').append(row);
      });
    });
  } else {
    alert('Invalid rankings!');
  }
  clearTeamInfoBox();
  adjustRankAndRowColor(true, true);
}

var warning = "You have unsaved changes! Please return to the page and save or click OK to discard your changes.";

function changeWeek(selectObj) {
	var unsaved = false;
	$('#ranking-table > tbody > tr:not(:first-child)').each(function() {
		if ($(this).hasClass('moved')) {
			unsaved = true;
			return false;
		}
	});
	if (!unsaved || confirm(warning)) {
		window.location = "/rank?week=" + selectObj[selectObj.selectedIndex].value;
	} else {
		return false;
	}
}

function submitDisplayAvgForm() {
	var unsaved = false;
	$('#ranking-table > tbody > tr:not(:first-child)').each(function() {
		if ($(this).hasClass('moved')) {
			unsaved = true;
			return false;
		}
	});
	if (!unsaved || confirm(warning)) {
		$('#update-display-avg-form').submit();
	} else {
		return false;
	}
}

function submitDisplayDVOAForm() {
	var unsaved = false;
	$('#ranking-table > tbody > tr:not(:first-child)').each(function() {
		if ($(this).hasClass('moved')) {
			unsaved = true;
			return false;
		}
	});
	if (!unsaved || confirm(warning)) {
		$('#update-display-dvoa-form').submit();
	} else {
		return false;
	}
}

function moveUp(teamRowId) {
	var teamId = $('#'+teamRowId).find('td:eq(3)').prop('id');
	var rank = $('#hidden-'+teamId).val();
	if (rank != 1) {
		jQuery('#'+teamRowId).prev().before(jQuery('#'+teamRowId));
		$('#'+teamRowId).addClass('moved');
		clearTeamInfoBox();
		adjustRankAndRowColor(true, false);
	}
}

function moveDown(teamRowId) {
	var teamId = $('#'+teamRowId).find('td:eq(3)').prop('id');
	var rank = $('#hidden-'+teamId).val();
	jQuery('#'+teamRowId).next().after(jQuery('#'+teamRowId));
	if (rank != 32) {
		$('#'+teamRowId).addClass('moved');
		clearTeamInfoBox();
		adjustRankAndRowColor(true, false);
	}
}

function keys(obj) {
	var keys = [];
	for (var key in obj) {
		keys.push(key);
	}
	return keys;
}

var currentTeamId = '';
var loadGif = $('<img />').prop('src', '//i.imgur.com/9NVqbRx.gif').prop('alt', 'loading');
var team_logo_mapping = {
  'ARI': '//i.imgur.com/eBCLhfo.png',
  'BAL': '//i.imgur.com/2W8S9sk.png',
  'ATL': '//i.imgur.com/HOrt09X.png',
  'DET': '//i.imgur.com/nvCgKX8.png',
  'BUF': '//i.imgur.com/jh2IILA.png',
  'CIN': '//i.imgur.com/pmagTxP.png',
  'IND': '//i.imgur.com/xqBQRpq.png',
  'TEN': '//i.imgur.com/HFR8qP1.png',
  'MIA': '//i.imgur.com/JDIaapm.png',
  'NYJ': '//i.imgur.com/CtPkafN.png',
  'CLE': '//i.imgur.com/hqh6UDM.png',
  'HOU': '//i.imgur.com/5Yqoc4N.png',
  'JAC': '//i.imgur.com/f5rxwnC.png',
  'MIN': '//i.imgur.com/hrSbJ80.png',
  'CHI': '//i.imgur.com/mhknbih.png',
  'CAR': '//i.imgur.com/TwPCje9.png',
  'TBB': '//i.imgur.com/XSZ4Tun.png',
  'KCC': '//i.imgur.com/XJAohW1.png',
  'DEN': '//i.imgur.com/oprzcsR.png',
  'DAL': '//i.imgur.com/ci3roHx.png',
  'NYG': '//i.imgur.com/vnRA0ek.png',
  'SEA': '//i.imgur.com/PzKfAjA.png',
  'RAM': '//i.imgur.com/RXpnWBP.png',
  'SFO': '//i.imgur.com/eusAn6o.png',
  'NEP': '//i.imgur.com/d2x3A8w.png',
  'PIT': '//i.imgur.com/oK2OtUR.png',
  'PHI': '//i.imgur.com/23CogLS.png',
  'WAS': '//i.imgur.com/bstfEdQ.png',
  'GBP': '//i.imgur.com/jtHzuOR.png',
  'SDC': '//i.imgur.com/DUXA4ax.png',
  'OAK': '//i.imgur.com/EAFY79R.png',
  'NOS': '//i.imgur.com/w1Id7n6.png'
}

function showTeamInfoBox(teamId, year) {
	var width = 162;

	$('.info-box').remove();
	if (teamId == currentTeamId) {
		currentTeamId = '';
		return;
	}
	currentTeamId = teamId;
	
	var infoBox = document.createElement('div');
	$(infoBox).prop('id', 'popup-'+teamId);
	$(infoBox).addClass('info-box');

	// Create content:
	var infoBoxContent = document.createElement('div');
	$(infoBoxContent).addClass('info-box-content');
	$(infoBoxContent).css('width', (width-20)+'px');
	$(infoBoxContent).append(loadGif);

	// Create arrow:
	var infoBoxArrow = document.createElement('div');
	$(infoBoxArrow).addClass('info-box-arrow');
	for (var i = 10; i >= 1; i--) {
		var arrowPiece = document.createElement('span');
		$(arrowPiece).addClass('info-box-arrow-piece');
		$(arrowPiece).addClass('info-box-arrow-'+i);
		$(infoBoxArrow).append(arrowPiece);
	}
	// Append content and arrow to box:
	$(infoBox).append(infoBoxContent);
	$(infoBox).append(infoBoxArrow);

	// Position the box:
	$(infoBox).css('position', 'absolute');
	$(infoBox).css('width', width);

	var rank = parseInt($('#'+teamId).parent().find('td:eq(0)').text());
   
  var multiplier = 20;
  if ($.browser.mozilla) {
    multiplier = 21;
  }
	var top = ($('#ranking-table').offset().top + 11 + rank) + ((rank-1) * multiplier);
	$(infoBox).css('top', top);

	var left = $('#ranking-table').offset().left - width - $('#ranking-table').offset().top;
	$(infoBox).css('left', left);

	// Display the box:
	$('body').append(infoBox);

	// Send request to get content:
	$.ajax({
		type: "GET",
		url: "/team?year="+year+"&id="+teamId,
		dataType: "xml",
		cache: false,

		success: function(xml) {
      // Add the offensive/defensive ranks:        
      var $rankTable = $('<table>');
      $rankTable.append($('<tr>').append(
				$('<th>').prop('colspan', 2).html('Offense'),		
				$('<th>').prop('colspan', 2).html('Defense')
			));
      $rankTable.append($('<tr>').append(
				$('<td>').html('Pass:'),		
        $('<td>').html($(xml).find("off_pass_rank").text()),
				$('<td>').html('Pass:'),
        $('<td>').html($(xml).find("def_pass_rank").text())
			));
      $rankTable.append($('<tr>').append(
				$('<td>').html('Rush:'),		
        $('<td>').html($(xml).find("off_rush_rank").text()),
				$('<td>').html('Rush:'),
        $('<td>').html($(xml).find("def_rush_rank").text())
			));
      var $rankDiv = $('<div class="offdef-rank-container">');
      $rankDiv.append($rankTable);

      // Add the matchup history:
      var count = 1;
			var $table = $('<table>');
			$table.prop('cellspacing', '0');
			$table.prop('cellpadding', '4');
			$table.css('width', $(infoBoxContent).width() - 10);
			
			$(xml).find("team").find("weeks").find("week").each(function() {
				var $row = $('<tr>');
				$row.addClass((count % 2 == 0) ? 'even' : 'odd');
				count++;
			
				var week = $(this).find("number").text();
				
				var opp = $(this).find("opponent").text();
				var oppImage = '<img '+
					'src="' + team_logo_mapping[opp.replace(/@/g,'')] + '" ' +
					'height="18" ' +
					'width="18" ' +
					'alt="'+opp.replace(/@/g,'')+'" ' +
					'title="'+opp.replace(/@/g,'')+'" ' +
					'style="border: 0; text-decoration: none;" />';
				
				var result = $(this).find("result").text();
				var score = '';
				if (result == 'W') {
					score += '<span class="green">W</span> ';
				} else if (result == 'L') {
					score += '<span class="red">L</span> ';
				} else {
					score += '<span>T</span> '
				}
				score += $(this).find("score").text();
								
				$table.append($row.append(
					$('<td>')
						.css('text-align', 'right')
						.css('font-weight', 'bold')
						.css('padding', '0 4px 2px 6px')
						.css('width', '19%')
						.html(week),
					
					$('<td>')
						.css('text-align', 'center')
						.css('padding', '0 3px 3px 2px')
						.html(opp.indexOf("@") != -1 ? '@' : 'vs'),
					
					$('<td>')
						.css('text-align', 'left')
						.css('padding', '0 8px 0 2px')
						.html(oppImage),
										
					$('<td>')
						.css('text-align', 'left')
						.css('padding-right', '5px')
						.css('padding-bottom', '5px')
						.html(score)
				));
			});
			
			$(infoBoxContent)
      .empty()
      //.append($rankDiv)
      .append($table);
		},

		error: function() { }
	});
}

function clearTeamInfoBox() {
	$('.info-box').remove();
	currentTeamId = '';
}
