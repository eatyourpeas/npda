/**
 * Draws a waffle chart on the given Konva stage.
 *
 * @param {Object} stage - The Konva stage where the chart will be drawn.
 * @param {Object} data - The data object where keys are categories and values are percentages.
 * @param {number} width - The width of the stage.
 * @param {number} height - The height of the stage.
 * @param {Object} COLORS - An object mapping categories to their respective colours.
 */
/**
 * Draws a waffle chart on the given Konva stage.
 *
 * @param {Object} stage - The Konva stage where the chart will be drawn.
 * @param {Object} data - The data object where keys are categories and values are percentages.
 * @param {number} width - The width of the stage.
 * @param {number} height - The height of the stage.
 * @param {Object} COLORS - An object mapping categories to their respective colours.
 */
export function drawWaffle(stage, data, width, height, COLORS) {
    // Clear the stage
    stage.destroyChildren();

    // Create a new layer
    const layer = new Konva.Layer();

    // Legend Configuration
    const legendTextStyle = {
        fontSize: 8,
        fontFamily: 'Montserrat',
        fill: 'black',
    };

    const legendGroup = new Konva.Group();
    const legendSquareSize = 10;
    const gapBetweenItems = 5; // Gap between legend items
    const gapBetweenLines = 10; // Gap between lines of legend items

    let legendXOffset = 0;
    let legendYOffset = 0;
    let totalLegendWidth = 0;

    // Add legend items
    Object.keys(data).forEach((key, index) => {
        // Add a colour square
        const colorSquare = new Konva.Rect({
            x: legendXOffset,
            y: legendYOffset,
            width: legendSquareSize,
            height: legendSquareSize,
            fill: COLORS[key],
            stroke: 'black',
            strokeWidth: 1,
        });
        legendGroup.add(colorSquare);

        // Add the text label
        const labelText = new Konva.Text({
            x: legendXOffset + legendSquareSize + 5,
            y: legendYOffset + 2,
            text: `${data[key]}% ${key}`,
            width: width / (Object.keys(data).length * 2), // Wrap text if it's too long
            align: 'left',
            ...legendTextStyle,
        });

        legendGroup.add(labelText);

        // Update X offset for the next legend item
        legendXOffset += colorSquare.width() + labelText.width() + gapBetweenItems;

        // Check if the next item exceeds the stage width
        if (legendXOffset > width) {
            legendXOffset = 0; // Reset X offset to the beginning
            legendYOffset += legendSquareSize + gapBetweenLines; // Move to the next line
        }

        // Track total legend width for centring
        if (index === Object.keys(data).length - 1) {
            totalLegendWidth = Math.max(totalLegendWidth, legendXOffset);
        }
    });

    // Centre the legend
    const legendStartXOffset = (width - totalLegendWidth) / 2;
    legendGroup.x(legendStartXOffset);
    layer.add(legendGroup);

    const gridSize = 10; // Fixed grid size (10x10)
    const totalSquares = gridSize * gridSize; // Total squares = 100
    const normalizedData = normalizeProportions(data, totalSquares, COLORS);

    // Flatten the proportions into a grid array of colours, each repeated `count` times
    const gridArray = normalizedData.flatMap(({ color, count }) =>
        Array(count).fill(color)
    );

    // Define square dimensions based on container aspect ratio
    const squareGap = 5;
    const squareWidth = (width - (gridSize - 1) * squareGap) / gridSize;
    const availableHeight = height - legendGroup.getClientRect().height - 10; // Subtract legend height and padding
    const squareHeight = (availableHeight - (gridSize - 1) * squareGap) / gridSize;

    // Use the smaller of squareWidth and squareHeight for uniform squares
    const squareSize = Math.min(squareWidth, squareHeight);

    // Calculate offsets to centre the grid within the container
    const xOffset = (width - (squareSize + squareGap) * gridSize + squareGap) / 2;
    const yOffset = legendGroup.getClientRect().height + 10; // Add padding below legend

    // Draw squares and group them by category
    gridArray.forEach((color, index) => {
        const row = Math.floor(index / gridSize);
        const col = index % gridSize;

        // Create a group for each category if it doesn't exist
        let group = layer.findOne(node => node.getAttr('category') === color);
        if (!group) {
            group = new Konva.Group({ category: color });
            layer.add(group);
        }

        // Create a square
        const square = new Konva.Rect({
            x: xOffset + col * (squareSize + squareGap),
            y: yOffset + row * (squareSize + squareGap),
            width: squareSize,
            height: squareSize,
            fill: color,
            stroke: 'black',
            strokeWidth: 0.5,
        });

        group.add(square);
    });

    // Add hover effects for interactivity
    // layer.getChildren().forEach(group => {
    //     group.on('mouseover', () => {
    //         group.getChildren().forEach(square => {
    //             // Lighten the square color on hover
    //             // const lighterColor = lightenHex(square.fill(), 0.5);
    //             // square.fill(lighterColor);
    //         });
    //     });

    //     group.on('mouseout', () => {
    //         group.getChildren().forEach(square => {
    //             // Undo the lightened color on mouseout
    //             // square.fill(group.getAttr('category'));
    //         });
    //     });
    // });

    // Add layer to the stage
    stage.add(layer);
}

/** 
When calculating pcts, floats converted to ints can lead to rounding errors
So check if the sum of the counts is 100 and adjust the first category if not
*/
function normalizeProportions(data, totalSquares, COLORS) {

    const squares = Object.entries(data).map(([key, pct]) => ({ color: COLORS[key], count: pct }));

    // Adjust counts to ensure the total equals `totalSquares`
    const totalCount = squares.reduce((sum, item) => sum + item.count, 0);
    const difference = totalSquares - totalCount;

    if (difference !== 0) {
        squares[0].count += difference; // Adjust the first category to fix the total
    }

    return squares;
}

/** 
Function to resize the stage dynamically
*/
export function resizeStage(stage, containerId, drawWaffle) {
    const container = document.getElementById(containerId);
    const width = container.offsetWidth;
    const height = container.offsetHeight;

    stage.width(width);
    stage.height(height);

    drawWaffle(stage, data, width, height); // Redraw the waffle chart with updated dimensions
}

function lightenHex(hexColor, lightnessFactor) {
    // Remove the '#' if present
    hexColor = hexColor.startsWith('#') ? hexColor.slice(1) : hexColor;

    // Convert hex to RGB
    const r = parseInt(hexColor.slice(0, 2), 16);
    const g = parseInt(hexColor.slice(2, 4), 16);
    const b = parseInt(hexColor.slice(4, 6), 16);

    // Increase brightness
    const newR = Math.min(Math.round(r + (255 - r) * lightnessFactor), 255);
    const newG = Math.min(Math.round(g + (255 - g) * lightnessFactor), 255);
    const newB = Math.min(Math.round(b + (255 - b) * lightnessFactor), 255);

    // Convert back to hex and return
    const toHex = (value) => value.toString(16).padStart(2, '0');
    return `#${toHex(newR)}${toHex(newG)}${toHex(newB)}`;
}
