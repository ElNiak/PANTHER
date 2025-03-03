
/**
 * Created by JetBrains PhpStorm.
 * User: bjost
 * Date: 7/13/11
 * Time: 10:48 AM
 * To change this template use File | Settings | File Templates.
 */

function nyanCat(width) {
    if(width.length > 0) {
        this.width = parseInt(width);
    } else {
        this.width = 100;
    }
    
    var progressContainer = document.getElementById('rainbowContainer');
    if (!progressContainer) {
        console.warn("rainbowContainer element not found");
        return; // Exit early if element doesn't exist
    }
    
    console.log(progressContainer.style.width);
    progressContainer.style.width = 75 + "%";

    this.setPercent = function(percent) {
        this.percent = parseInt(percent);
        
        var progress = document.getElementById('rainbow');
        var cat = document.getElementById('nyanCat');
        
        if (!progress || !cat) {
            console.warn("rainbow or nyanCat element not found");
            return;
        }

        this.pixels = (this.percent / 100) * progressContainer.offsetWidth;
        progress.style.width = this.pixels.toString() + "px";

        var catProgress = this.pixels;
        cat.style.left = catProgress.toString() + "px";
    }; //percent
} //nyanCat
