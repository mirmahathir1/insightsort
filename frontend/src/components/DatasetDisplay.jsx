// import React, { useState, useMemo } from "react";
// import { DataGrid } from "@mui/x-data-grid";


// const colorPalette = [
//     '#1f77b4', // Blue
//     '#ff7f0e', // Orange
//     '#2ca02c', // Green
//     '#d62728', // Red
//     '#9467bd', // Purple
//     '#8c564b', // Brown
//     '#e377c2', // Pink
//     '#7f7f7f', // Gray
//     '#bcbd22', // Olive
//     '#17becf', // Cyan
//     '#393b79', // Dark Blue
//     '#9c9ede', // Light Blue
//     '#8c6d31', // Dark Brown
//     '#e7ba52', // Light Brown
//     '#637939', // Dark Green
//     '#e7969c', // Light Pink
//     '#843c39', // Dark Red
//     '#d6616b', // Medium Red
//     '#7b4173', // Dark Purple
//     '#a55194', // Medium Purple
//   ];
  
// let colorIndex = 0;

// const DatasetDisplay = ({ sortedDatasets, levenshteinDistances }) => {
//   if (!sortedDatasets || Object.keys(sortedDatasets).length === 0) {
//     return <p>No datasets available.</p>;
//   }

//   const datasetKeys = Object.keys(sortedDatasets); // Get the list of dataset names
//   const [activeDatasetIndex, setActiveDatasetIndex] = useState(0); // Track the currently active dataset

//   const [colorMap, setColorMap] = useState({});
//   const [colorColumn, setColorColumn] = useState(datasetKeys[0]);
//   // Handler for moving to the next dataset
//   const handleNext = () => {
//     setColorMap({});
//     colorIndex = 0;
//     setActiveDatasetIndex((prevIndex) =>
//       prevIndex === datasetKeys.length - 1 ? 0 : prevIndex + 1
//     );
//   };

//   const handlePrev = () => {
//     setColorMap({});
//     colorIndex = 0;
//     setActiveDatasetIndex((prevIndex) =>
//       prevIndex === 0 ? datasetKeys.length - 1 : prevIndex - 1
//     );
//   };

//   const assignColorToValue = useMemo(() => {
//     let localColorMap = { ...colorMap }; // Use local copy to avoid excessive state changes
//     return (value) => {
//       if (!localColorMap[value]) {
//         const newColor = colorPalette[colorIndex % colorPalette.length];
//         localColorMap[value] = newColor;
//         colorIndex++;
//         setColorMap(localColorMap); // Only update state when a new color is assigned
//       }
//       return localColorMap[value];
//     };
//   }, [colorMap]);

//   const renderColoredCell = (params) => {
//     const value = params.value;
//     const color = assignColorToValue(value);
//     return <span style={{ color: color, fontWeight: 'bold' }}>{value}</span>;
//   };

//   const activeDatasetName = datasetKeys[activeDatasetIndex];
//   const activeDatasetRows = sortedDatasets[activeDatasetName] || [];

//   if (!activeDatasetRows || activeDatasetRows.length === 0) {
//     return <p>No data available for the dataset "{activeDatasetName}".</p>;
//   }

//   // Columns for DataGrid (assuming the first row has all the keys as column names)
//   const columns =
//     activeDatasetRows.length > 0
//       ? Object.keys(activeDatasetRows[0]).map((key) => ({
//           field: key,
//           headerName: key,
//           width: 150,
          
//         }))
//       : [];

//   // Rows for DataGrid
//   const rows = activeDatasetRows.map((row, index) => ({
//     id: index + 1,
//     ...row,
//   }));

//   const levenshteinMessages = Object.entries(levenshteinDistances).map(([key, distance], index) => (
//     <p key={index}>
//       {key} : {distance}.
//     </p>
//   ));


//   return (
//     <div>
//       <h2>Sorted Dataset: {activeDatasetName}</h2>

//       {/* Display dataset in DataGrid */}
//       <div className="table-div" style={{ height: 800, width: '80%' }}>
//               <DataGrid rows={rows} columns={columns} pageSize={10} />
//     </div>

//     {/* Display Levenshtein distances */}
//     <div style={{ marginTop: "20px" }}>
//         <h3>Levenshtein Distances:</h3>
//         {levenshteinMessages}
//       </div>

//       {/* Scroll Buttons */}
//       <div style={{ marginTop: "1rem", marginBottom: "2rem", display: "flex", justifyContent: "center" }}>
//         <button onClick={handlePrev} style={{ marginRight: "10px" }}>
//           Previous
//         </button>
//         <button onClick={handleNext}>Next</button>
//       </div>
//     </div>
//   );
// };

// export default DatasetDisplay;



import React, { useState, useMemo } from "react";
import { DataGrid } from "@mui/x-data-grid";

const colorPalette = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b',
    '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#393b79', '#9c9ede',
    '#8c6d31', '#e7ba52', '#637939', '#e7969c', '#843c39', '#d6616b',
    '#7b4173', '#a55194',
];

let colorIndex = 0;

const DatasetDisplay = ({ sortedDatasets, levenshteinDistances }) => {
  if (!sortedDatasets || Object.keys(sortedDatasets).length === 0) {
    return <p>No datasets available.</p>;
  }

  const datasetKeys = Object.keys(sortedDatasets); // Get the list of dataset names
  const [activeDatasetIndex, setActiveDatasetIndex] = useState(0); // Track the currently active dataset

  const [colorMap, setColorMap] = useState({});
  const [colorColumn, setColorColumn] = useState(datasetKeys[0]);

  // Handler for moving to the next dataset
  const handleNext = () => {
    setColorMap({});
    colorIndex = 0;
    setActiveDatasetIndex((prevIndex) =>
      prevIndex === datasetKeys.length - 1 ? 0 : prevIndex + 1
    );
  };

  const handlePrev = () => {
    setColorMap({});
    colorIndex = 0;
    setActiveDatasetIndex((prevIndex) =>
      prevIndex === 0 ? datasetKeys.length - 1 : prevIndex - 1
    );
  };

  const assignColorToValue = useMemo(() => {
    let localColorMap = { ...colorMap }; // Use local copy to avoid excessive state changes
    return (value) => {
      if (!localColorMap[value]) {
        const newColor = colorPalette[colorIndex % colorPalette.length];
        localColorMap[value] = newColor;
        colorIndex++;
        setColorMap(localColorMap); // Only update state when a new color is assigned
      }
      return localColorMap[value];
    };
  }, [colorMap]);

  const renderColoredCell = (params) => {
    const value = params.value;
    const color = assignColorToValue(value);
    return <span style={{ color: color, fontWeight: 'bold' }}>{value}</span>;
  };

  const activeDatasetName = datasetKeys[activeDatasetIndex];
  const activeDatasetRows = sortedDatasets[activeDatasetName] || [];

  // Ensure activeDatasetRows is an array before using .map()
  if (!Array.isArray(activeDatasetRows) || activeDatasetRows.length === 0) {
    return <p>No data available for the dataset "{activeDatasetName}".</p>;
  }

  // Columns for DataGrid (assuming the first row has all the keys as column names)
  const columns = Object.keys(activeDatasetRows[0] || {}).map((key) => ({
    field: key,
    headerName: key,
    width: 150,
  }));

  // Rows for DataGrid
  const rows = activeDatasetRows.map((row, index) => ({
    id: index + 1,
    ...row,
  }));

  const levenshteinMessages = Object.entries(levenshteinDistances).map(([key, distance], index) => (
    <p key={index}>
      {key} : {distance}.
    </p>
  ));

  return (
    <div>
      <h2>Sorted Dataset: {activeDatasetName}</h2>
      {console.log(sortedDatasets)}

      {/* Display dataset in DataGrid */}
      <div className="table-div" style={{ height: 800, width: '80%' }}>
        <DataGrid rows={rows} columns={columns} pageSize={10} />
      </div>

      {/* Display Levenshtein distances */}
      <div style={{ marginTop: "20px" }}>
        <h3>Levenshtein Distances:</h3>
        {levenshteinMessages}
      </div>

      {/* Scroll Buttons */}
      <div style={{ marginTop: "1rem", marginBottom: "2rem", display: "flex", justifyContent: "center" }}>
        <button onClick={handlePrev} style={{ marginRight: "10px" }}>
          Previous
        </button>
        <button onClick={handleNext}>Next</button>
      </div>
    </div>
  );
};

export default DatasetDisplay;



// Multiple datasets
// after fall break // the below code works perfectly


// import React, { useState, useMemo, useEffect } from "react";
// import { DataGrid } from "@mui/x-data-grid";

// const colorPalette = [
//   '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b',
//   '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#393b79', '#9c9ede',
//   '#8c6d31', '#e7ba52', '#637939', '#e7969c', '#843c39', '#d6616b',
//   '#7b4173', '#a55194',
// ];

// let colorIndex = 0;

// const DatasetDisplay = ({ sortedDatasets = {}, levenshteinDistances = {}, sortingCriterias = {} }) => {
//   if (!sortedDatasets || Object.keys(sortedDatasets).length === 0) {
//     return <p>No datasets available.</p>;
//   }

//   const datasetNames = Object.keys(sortedDatasets); // Get dataset names

//   // Ensure that activeDatasetName is initialized
//   const [activeDatasetName, setActiveDatasetName] = useState(datasetNames[0]);

//   // Ensure that sortingKey is initialized based on the first dataset
//   const [sortingKey, setSortingKey] = useState(
//     Object.keys(sortedDatasets[datasetNames[0]])[0] || ""
//   );

//   // Initialize sorting criteria based on the first dataset and column
//   const [sortingCriteria, setSortingCriteria] = useState(
//     (sortingCriterias[datasetNames[0]] && sortingCriterias[datasetNames[0]][sortingKey]) || ""
//   );

//   // Use effect to update sortingKey and sortingCriteria when the active dataset changes
//   useEffect(() => {
//     if (sortedDatasets[activeDatasetName]) {
//       const firstColumn = Object.keys(sortedDatasets[activeDatasetName])[0];
//       setSortingKey(firstColumn);
//       setSortingCriteria(sortingCriterias[activeDatasetName]?.[firstColumn] || "");
//     }
//   }, [activeDatasetName, sortedDatasets, sortingCriterias]);

//   const [colorMap, setColorMap] = useState({});
//   const [colorColumn, setColorColumn] = useState(sortingKey);

//   const assignColorToValue = useMemo(() => {
//     let localColorMap = { ...colorMap }; // Use local copy to avoid excessive state changes
//     return (value) => {
//       if (!localColorMap[value]) {
//         const newColor = colorPalette[colorIndex % colorPalette.length];
//         localColorMap[value] = newColor;
//         colorIndex++;
//         setColorMap(localColorMap); // Only update state when a new color is assigned
//       }
//       return localColorMap[value];
//     };
//   }, [colorMap]);

//   const renderColoredCell = (params) => {
//     const value = params.value;
//     const color = assignColorToValue(value);
//     return <span style={{ color: color, fontWeight: 'bold' }}>{value}</span>;
//   };

//   const handleDatasetChange = (e) => {
//     setActiveDatasetName(e.target.value);
//     setColorMap({});
//     colorIndex = 0;
//   };

//   const handleSortingKeyChange = (e) => {
//     setSortingKey(e.target.value);
//     setSortingCriteria(sortingCriterias[activeDatasetName]?.[e.target.value] || "");
//     setColorMap({});
//     colorIndex = 0;
//   };

//   const activeDataset = sortedDatasets[activeDatasetName];
//   const sortedRows = activeDataset?.[sortingKey] || []; // Get the sorted rows based on the selected sorting column

//   if (!sortedRows || sortedRows.length === 0) {
//     return <p>No data available for the selected dataset or sorting column.</p>;
//   }

//   // Dynamically create columns for DataGrid (from the first row's keys)
//   const columns = Object.keys(sortedRows[0]).map((key) => ({
//     field: key,
//     headerName: key,
//     width: 150,
//     renderCell: key === colorColumn ? renderColoredCell : null,
//   }));

//   // Prepare rows for DataGrid
//   const rows = sortedRows.map((row, index) => ({
//     id: index + 1, // Add an ID for each row (required by DataGrid)
//     ...row, // Spread the row data
//   }));

//   const levenshteinMessages = Object.entries(levenshteinDistances).map(([key, distance], index) => (
//     <p key={index}>
//       {key} : {distance}
//     </p>
//   ));

//   return (
//     <div>
//       <h2>Sorted Datasets</h2>

//       <label htmlFor="datasetSelect">Choose Dataset: </label>
//       <select id="datasetSelect" value={activeDatasetName} onChange={handleDatasetChange}>
//         {datasetNames.map((datasetName) => (
//           <option key={datasetName} value={datasetName}>
//             {datasetName}
//           </option>
//         ))}
//       </select>

//       <label htmlFor="sortingSelect">Choose Column: </label>
//       <select id="sortingSelect" value={sortingKey} onChange={handleSortingKeyChange}>
//         {Object.keys(activeDataset || {}).map((colName) => (
//           <option key={colName} value={colName}>
//             {colName}
//           </option>
//         ))}
//       </select>

//       {/* DataGrid to Display Sorted Rows */}
//       <div style={{ height: 800, width: '100%', marginTop: '20px' }}>
//         <DataGrid rows={rows} columns={columns} pageSize={10} />
//       </div>

//       <p>{sortingCriteria}</p>
//     </div>
//   );
// };

// export default DatasetDisplay;





// after fall break, trying displaying datasets on the left


// import React, { useMemo, useState, useEffect } from "react";
// import { DataGrid } from "@mui/x-data-grid";

// const DatasetDisplay = ({ activeDatasetName, sortingKey, sortedDatasets, sortingCriterias, levenshteinDistances }) => {
//   const activeDataset = sortedDatasets[activeDatasetName];
//   const sortedRows = activeDataset?.[sortingKey] || [];
//   const [levenshteinToShow, setLevenshteinToSHow] = useState([])

//   useEffect(() => {
//     const levenshteinDictForActiveDataset = levenshteinDistances[activeDatasetName]
//     const dictKeys = Object.keys(levenshteinDictForActiveDataset)

//     const levenshteinDistancesForSortingKey = []
//     dictKeys.forEach((key) => {
//       if (key.includes(sortingKey)){
//         levenshteinDistancesForSortingKey.push([`Levenshtein Distance of ${key} is:`, levenshteinDictForActiveDataset[key]])
//       }
//     })

//     levenshteinDistancesForSortingKey.sort((a, b) => b[1] - a[1]);
//     setLevenshteinToSHow(levenshteinDistancesForSortingKey);
//   }, [activeDatasetName, sortingKey, levenshteinDistances])

//   if (!sortedRows || sortedRows.length === 0) {
//     return <p>No data available for the selected dataset or sorting column.</p>;
//   }

//   const columns = Object.keys(sortedRows[0]).map((key) => ({
//     field: key,
//     headerName: key,
//     width: 150,
//   }));

//   const rows = sortedRows.map((row, index) => ({
//     id: index + 1,
//     ...row,
//   }));

//   const sortingCriteria = sortingCriterias[activeDatasetName]?.[sortingKey] || "No sorting criteria available";
//   const formattedCriteria = sortingCriteria.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

//   return (
//     <div>
//       <h2>Sorted Dataset: {activeDatasetName}</h2>
//       <p>Sorting by: {sortingKey}</p>
//       <p dangerouslySetInnerHTML={{ __html: formattedCriteria }} />

//       <div style={{ height: 800, width: '100%', marginTop: '20px' }}>
//         <DataGrid rows={rows} columns={columns} pageSize={10} />
//       </div>

//       <div className="levenshtein_display">
//       {levenshteinToShow.map((element) => <p>{element}</p>)}
//       </div>
//     </div>
//   );
// };

// export default DatasetDisplay;
