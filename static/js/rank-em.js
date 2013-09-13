
$(document).ready(function() {
	$("#ranking-table").tableDnD({
		onDragStart: clearTeamInfoBox,
		onDragClass: "drag-row",
		onDrop: function(table, row) {
			$(row).addClass('moved');
			adjustRankAndRowColor(true, false);
		}
	});
});

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
	var teamId = $('#'+teamRowId).find('td:eq(3)').attr('id');
	var rank = $('#hidden-'+teamId).val();
	if (rank != 1) {
		jQuery('#'+teamRowId).prev().before(jQuery('#'+teamRowId));
		$('#'+teamRowId).addClass('moved');
		clearTeamInfoBox();
		adjustRankAndRowColor(true, false);
	}
}

function moveDown(teamRowId) {
	var teamId = $('#'+teamRowId).find('td:eq(3)').attr('id');
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

//var loadGif = $('<img />').attr('src', '/images/ajax-loader.gif').attr('alt', 'loading');
var currentTeamId = '';

function showTeamInfoBox(teamId, year) {
	var width = 162;

	$('.info-box').remove();
	if (teamId == currentTeamId) {
		currentTeamId = '';
		return;
	}
	currentTeamId = teamId;
	
	var infoBox = document.createElement('div');
	$(infoBox).attr('id', 'popup-'+teamId);
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
				$('<th>').attr('colspan', 2).html('Offense'),		
				$('<th>').attr('colspan', 2).html('Defense')
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
			$table.attr('cellspacing', '0');
			$table.attr('cellpadding', '4');
			$table.css('width', $(infoBoxContent).width() - 10);
			
			$(xml).find("team").find("weeks").find("week").each(function() {
				var $row = $('<tr>');
				$row.addClass((count % 2 == 0) ? 'even' : 'odd');
				count++;
			
				var week = $(this).find("number").text();
				
				var opp = $(this).find("opponent").text();
				var oppImage = '<img '+
					'src="/images/'+opp.replace(/@/g,'')+'.png" ' +
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
			
			$(infoBoxContent).empty().append($rankDiv).append($table);
		},

		error: function() { }
	});
}

function clearTeamInfoBox() {
	$('.info-box').remove();
	currentTeamId = '';
}
