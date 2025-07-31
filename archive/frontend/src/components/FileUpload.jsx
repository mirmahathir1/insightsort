// import React, { useRef, useState, useMemo } from "react";
// import axios from "axios";
// import { RotatingLines } from "react-loader-spinner";
// import { DataGrid } from '@mui/x-data-grid';
// import DatasetDisplay from "./DatasetDisplay";

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
  
// const FileUpload = () => {
//   const [file, setFile] = useState(null);
//   const [columnName, setColumnName] = useState("");
//   const [action, setAction] = useState("");
//   const [message, setMessage] = useState("");
//   const [result, setResult] = useState([]);
//   const [column1, setColumn1] = useState("");
//   const [column2, setColumn2] = useState("");
//   const [dataset, setDataset] = useState([]);
//   const [constraints, setConstraints] = useState("")
//   const [loading, setLoading] = useState(false);
//   const [timings, setTimings] = useState([]);

//   const fileInputRef = useRef(null);

//   const [sortedDatasets, setSortedDatasets] = useState({});
//   const [levenshteinDistances, setLevenshteinDistances] = useState({});

//   // applying colors to column cells
//   const [colorMap, setColorMap] = useState({});
//   const [colorColumn, setColorColumn] = useState();

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

//   const handleFileChange = (e) => {
//     setFile(e.target.files[0]);
//   };

//   const handleColumnNameChange = (e) => {
//     setColumnName(e.target.value);
//   };

//   const handleActionChange = (e) => {
//     setAction(e.target.value);
//   };

//   const handleColumn1Change = (e) => {
//     setColumn1(e.target.value);
//   };

//   const handleColumn2Change = (e) => {
//     setColumn2(e.target.value);
//   };

//   const handleConstraintChange = (e) => {
//     setConstraints(e.target.value);
//   }

//   const handleFileUpload = async () => {
//     const formData = new FormData();
//     formData.append("file", file);
//     formData.append("action", action);
//     formData.append("constraints", constraints)

//     console.log(action)
//     setSortedDatasets({})
//     setColorMap({});
//     colorIndex = 0;


//     if (action === "single_column_sort") {
//       formData.append("column_name", columnName);
//     }

//     if (
//       action === "sort_multiple_columns" ||
//       action === "generate_new_column"
//     ) {
//       formData.append("column1", column1);
//       formData.append("column2", column2);
//     }

//     setLoading(true);

//     try {
//       const res = await axios.post(
//         "http://127.0.0.1:5000/process_dataset",
//         formData,
//         {
//           headers: {
//             "Content-Type": "multipart/form-data",
//           },
//         }
//       );

//       if (action === "single_column_sort") {
//         setMessage(
//           `Column processed: ${columnName}. Constraints: ${constraints}`
//         );
//         const timing = res.data.timing;
//         console.log(res.data)
//         const cleanedResult = res.data.sorting_result.map((line) =>
//           line.replace(/^###\s*/, "").replace(/\*\*/g, "")
//         );
//         setColorColumn(columnName);
//         setResult(cleanedResult);
//         if (timing) {
//           setMessage(`Sorted dataset on column ${columnName} successfully in ${timing}.`);
//         }
//       } else if(action === "give_sorting_suggestions"){
//         setMessage("Suggestions generated successfully.");
//         let responseData = res.data;
//         if (typeof res.data === 'string') {
//             responseData = JSON.parse(res.data);
//         }
//         setSortedDatasets(responseData.sorted_datasets);
//         setLevenshteinDistances(responseData.levenshtein_distances);
//         const timings = responseData.timings; 
//         const formattedTimings = Object.entries(timings).map(
//           ([key, value]) => `${key}: ${value}`
//         ); // Format timings into readable strings
//         setTimings(formattedTimings); // Save timings in state
//       }else if (action === "column_suggestions" || action === "determine_columns") {
//         setMessage("Suggestions generated successfully.");
//         const timing = res.data.timing;
//         const cleanedResult = res.data.suggestions.map((line) =>
//           line.replace(/^###\s*/, "").replace(/\*\*/g, "")
//         );
//         setResult(cleanedResult.filter((line) => line.trim() !== ""));
//         if (timing) {
//           setMessage(`Suggestions generated successfully in ${timing}.`);
//         }
//       } else if (action === "sort_multiple_columns") {
//         setMessage(`Rows sorted based on multiple columns. Constraints: ${constraints}`);
//         const cleanedResult = res.data.sorting_result.map((line) =>
//           line.replace(/^###\s*/, "").replace(/\*\*/g, "")
//         );
//         setResult(cleanedResult.filter((line) => line.trim() !== ""));
//       } else if (action === "suggest_dataset_purpose") {
//         setMessage("Here is what the dataset can be about: ");
//         setResult(res.data.suggestion);
//       } else if (action == "generate_new_column") {
//         setMessage("New data: ");
//         const cleanedResult = res.data.sorting_result.map((line) =>
//           line.replace(/^###\s*/, "").replace(/\*\*/g, "")
//         );
//         setResult(cleanedResult.filter((line) => line.trim() !== ""));
//       }
//       setDataset(res.data.dataset);
//     } catch (err) {
//       console.error(err);
//       setMessage("File upload failed or invalid input.");
//       setResult([]);
//     } finally{
//         setLoading(false);
//     }
//   };

//   const handleDrop = (e) => {
//     e.preventDefault();
//     const droppedFile = e.dataTransfer.files[0];
//     setFile(droppedFile);
//   };

//   const handleDragOver = (e) => {
//     e.preventDefault();
//   };

//   const handleClick = () => {
//     fileInputRef.current.click();
//   };

//   // Define the columns for the DataGrid
//   const columns = dataset && dataset.length > 0
//     ? Object.keys(dataset[0]).map((key) => ({
//         field: key,
//         headerName: key,
//         width: 150,
//         renderCell: key === colorColumn ? renderColoredCell : null,
//       }))
//     : [];

//   // Define the rows for the DataGrid
//   const rows = dataset && dataset.map((row, index) => ({
//     id: index + 1,
//     ...row,
//   }));

//   return (
//     <div>
//       <h2>Upload Dataset</h2>
//       <div
//         className="drop-zone"
//         onDrop={handleDrop}
//         onDragOver={handleDragOver}
//         onClick={handleClick}
//       >
//         {file ? (
//           <p>{file.name}</p>
//         ) : (
//           <p>Drag & drop a file here, or click to select one</p>
//         )}
//         <input
//           type="file"
//           onChange={handleFileChange}
//           ref={fileInputRef}
//           style={{ display: "none" }}
//         />
//       </div>
//       <div className="select-buttons">
//         <h3>Select Action</h3>
//         <div className="radio-btns">
//           <div>
//             <input
//               type="radio"
//               name="action"
//               value="suggest_dataset_purpose"
//               onChange={handleActionChange}
//             />{" "}
//             Suggest what is the dataset about
//           </div>
//           <div>
//             <input
//               type="radio"
//               name="action"
//               value="determine_columns"
//               onChange={handleActionChange}
//             />{" "}
//             Columns that can be used to semantically sort the dataset
//           </div>
//           <div>
//             <input
//               type="radio"
//               name="action"
//               value="give_sorting_suggestions"
//               onChange={handleActionChange}
//             />{" "}
//             Give sorted datasets
//           </div>
//           <div>
//             <input
//               type="radio"
//               name="action"
//               value="single_column_sort"
//               onChange={handleActionChange}
//             />{" "}
//             Sort using a single column
//           </div>
//           <div>
//             <input
//               type="radio"
//               name="action"
//               value="column_suggestions"
//               onChange={handleActionChange}
//             />{" "}
//             Get column pair suggestions for sorting
//           </div>
//           <div>
//             <input
//               type="radio"
//               name="action"
//               value="sort_multiple_columns"
//               onChange={handleActionChange}
//             />{" "}
//             Sort using two columns
//           </div>
//           <div>
//             <input
//               type="radio"
//               name="action"
//               value="generate_new_column"
//               onChange={handleActionChange}
//             />{" "}
//             Create a new column from multiple columns
//           </div>
//         </div>
//       </div>

//       {action === "single_column_sort" && (
//         <>
//         <div className="input">
//           <label>Column Name: </label>
//           <input
//             type="text"
//             placeholder="Enter column name"
//             value={columnName}
//             onChange={handleColumnNameChange}
//           />
//         </div>
//         <div className="input">
//             <label>Constraint: </label>
//             <input type="text" className="column-input" placeholder="Enter any constraints" value={constraints} onChange={handleConstraintChange}/>
//         </div>
//         </>
//       )}

//       {action === "sort_multiple_columns" && (
//         <>
//         <div className="input">
//           <label>Column 1: </label>
//           <input
//             type="text"
//             placeholder="Enter first column name"
//             value={column1}
//             onChange={handleColumn1Change}
//           />
//           <br />
//           <label>Column 2: </label>
//           <input
//             type="text"
//             placeholder="Enter second column name"
//             value={column2}
//             onChange={handleColumn2Change}
//           />
//         </div>
//         <div className="input">
//         <label>Constraint: </label>
//         <input type="text" placeholder="Enter any constraints" value={constraints} onChange={handleConstraintChange}/>
//         </div>
//         </>
//       )}

//       {action === "generate_new_column" && (
//         <div className="input">
//           <label>Column 1: </label>
//           <input
//             type="text"
//             placeholder="Enter first column name"
//             value={column1}
//             onChange={handleColumn1Change}
//           />
//           <br />
//           <label>Column 2: </label>
//           <input
//             type="text"
//             placeholder="Enter second column name"
//             value={column2}
//             onChange={handleColumn2Change}
//           />
//         </div>
//       )}

//       <div className="upload-btn-div">
//       <button className="upload-btn" onClick={handleFileUpload}>Upload</button>
//       </div>
//       <p>{message}</p>
//       {loading ? (
//         <div className="loader">
//           <RotatingLines
//             strokeColor="blue"
//             strokeWidth="3"
//             animationDuration="0.75"
//             width="70"
//             visible={true}
//           />
//         </div>
//       ) : (
//         <>
//           {dataset && dataset.length > 0 && (
//             <div className="table-div" style={{ height: 600, width: '80%' }}>
//               <DataGrid rows={rows} columns={columns} pageSize={10} />
//             </div>
//           )}
//           {result.length > 0 && (
//             <div>
//               <h3>Result:</h3>
//               <ul>
//                 {result.map((item, index) => (
//                   <p key={index}>{item}</p>
//                 ))}
//               </ul>
//             </div>
//           )}
//         </>
//       )}
//       {timings.length > 0 && (
//   <div>
//     <h3>Task Timings:</h3>
//     <ul>
//       {timings.map((timing, index) => (
//         <li key={index}>{timing}</li>
//       ))}
//     </ul>
//   </div>
// )}
//       {sortedDatasets && <DatasetDisplay sortedDatasets={sortedDatasets} levenshteinDistances={levenshteinDistances}/>}
//     </div>
//   );
// };

// export default FileUpload;



// MULTIPLE DATASETS

// oct 1st week

// import React, { useRef, useState, useMemo } from "react";
// import axios from "axios";
// import { RotatingLines } from "react-loader-spinner";
// import { DataGrid } from '@mui/x-data-grid';
// import DatasetDisplay from "./DatasetDisplay";
// import JoinedDatasetDisplay from "./JoinedDatasetDisplay";

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

// const FileUpload = () => {
//   const [files, setFiles] = useState([]);
//   const [message, setMessage] = useState("");
//   const [result, setResult] = useState([]);
//   const [dataset, setDataset] = useState([]);
//   const [loading, setLoading] = useState(false);
//   const fileInputRef = useRef(null);
//   const [sortedDatasets, setSortedDatasets] = useState({});
//   const [levenshteinDistances, setLevenshteinDistances] = useState({});

//   // multiple datasets debugging
//   const [suggestion, setSuggestion] = useState('')
//   const [joinedDatasets, setJoinedDatasets] = useState({})

//   // Drag and Drop handlers
//   const handleDrop = (e) => {
//     e.preventDefault();
//     const droppedFiles = Array.from(e.dataTransfer.files); // Extract files from drag event
//     setFiles((prevFiles) => [...prevFiles, ...droppedFiles]); // Append the files to the current list
//   };

//   const handleDragOver = (e) => {
//     e.preventDefault(); // Allow the drop event to occur
//   };

//   const handleFileChange = (e) => {
//     const selectedFiles = Array.from(e.target.files); // Get files from input
//     setFiles((prevFiles) => [...prevFiles, ...selectedFiles]); // Append the selected files to the list
//   };

//   const handleClick = () => {
//     fileInputRef.current.click(); // Programmatically trigger file input click
//   };

//   const handleMultipleFileUpload = async () => {
//     const formData = new FormData();

//     if (files.length > 1) {
//       for (let i = 0; i < files.length; i++) {
//         formData.append("files[]", files[i]);
//       }
//     } else {
//       alert("Please upload at least two files");
//       return;
//     }

//     setLoading(true);

//     try {
//       const res = await axios.post(
//         "http://127.0.0.1:5000/process_multiple_datasets",
//         formData,
//         {
//           headers: {
//             "Content-Type": "multipart/form-data",
//           },
//         }
//       );

//       setMessage("Joinable datasets identified and suggestions generated successfully.");

//       let responseData = res.data;
//       if (typeof res.data === 'string') {
//         responseData = JSON.parse(res.data);
//       }

//       setSuggestion(responseData.suggestions)
//       setJoinedDatasets(responseData.joined_datasets)
//       setSortedDatasets(responseData.sorted_datasets);
//       setLevenshteinDistances(responseData.levenshtein_distances);

//     } catch (err) {
//       console.error(err);
//       setMessage("File upload failed or invalid input.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   // Define the columns for the DataGrid
//   const columns = dataset && dataset.length > 0
//     ? Object.keys(dataset[0]).map((key) => ({
//         field: key,
//         headerName: key,
//         width: 150,
//       }))
//     : [];

//   // Define the rows for the DataGrid
//   const rows = dataset && dataset.map((row, index) => ({
//     id: index + 1,
//     ...row,
//   }));

//   return (
//     <div>
//       <h2>Upload Multiple Datasets</h2>
//       <div
//         className="drop-zone"
//         onDrop={handleDrop}
//         onDragOver={handleDragOver}
//         onClick={handleClick}
//       >
//         {files.length > 0 ? (
//           <p>{files.map(file => file.name).join(", ")}</p>
//         ) : (
//           <p>Drag & drop multiple files here, or click to select files</p>
//         )}
//         <input
//           type="file"
//           multiple
//           onChange={handleFileChange}
//           ref={fileInputRef}
//           style={{ display: "none" }}
//         />
//       </div>

//       <button onClick={handleMultipleFileUpload} disabled={files.length === 0}>
//         Upload Files
//       </button>
      
//       <p>{message}</p>

//       {loading ? (
//         <div className="loader">
//           <RotatingLines
//             strokeColor="blue"
//             strokeWidth="3"
//             animationDuration="0.75"
//             width="70"
//             visible={true}
//           />
//         </div>
//       // ) : (
//       //   <>
//       //     {dataset && dataset.length > 0 && (
//       //       <div className="table-div" style={{ height: 600, width: '80%' }}>
//       //         <DataGrid rows={rows} columns={columns} pageSize={10} />
//       //       </div>
//       //     )}
//       //     {sortedDatasets && <DatasetDisplay sortedDatasets={sortedDatasets} levenshteinDistances={levenshteinDistances} />}
//       //   </>
//       // )}

//       ):(
//         <>
//         {suggestion && suggestion.map(item => <p>{item}</p>)}
//         {joinedDatasets && <JoinedDatasetDisplay joinedDatasets={joinedDatasets}/>}
//         {sortedDatasets && <DatasetDisplay sortedDatasets={sortedDatasets} levenshteinDistances={levenshteinDistances} />}

//         </>
//       )}
//     </div>
//   );
// };

// export default FileUpload;




// MULTIPLE DATASETS

// after fall break // this code works perfectly

// import React, { useRef, useState, useMemo } from "react";
// import axios from "axios";
// import { RotatingLines } from "react-loader-spinner";
// import { DataGrid } from '@mui/x-data-grid';
// import DatasetDisplay from "./DatasetDisplay";
// import JoinedDatasetDisplay from "./JoinedDatasetDisplay";

// const colorPalette = [
//       '#1f77b4', // Blue
//       '#ff7f0e', // Orange
//       '#2ca02c', // Green
//       '#d62728', // Red
//       '#9467bd', // Purple
//       '#8c564b', // Brown
//       '#e377c2', // Pink
//       '#7f7f7f', // Gray
//       '#bcbd22', // Olive
//       '#17becf', // Cyan
//       '#393b79', // Dark Blue
//       '#9c9ede', // Light Blue
//       '#8c6d31', // Dark Brown
//       '#e7ba52', // Light Brown
//       '#637939', // Dark Green
//       '#e7969c', // Light Pink
//       '#843c39', // Dark Red
//       '#d6616b', // Medium Red
//       '#7b4173', // Dark Purple
//       '#a55194', // Medium Purple
//     ];;

// let colorIndex = 0;

// const FileUpload = () => {
//   const [files, setFiles] = useState([]);
//   const [message, setMessage] = useState("");
//   const [result, setResult] = useState([]);
//   const [dataset, setDataset] = useState([]);
//   const [loading, setLoading] = useState(false);
//   const fileInputRef = useRef(null);
//   const [sortedDatasets, setSortedDatasets] = useState({});
//   const [levenshteinDistances, setLevenshteinDistances] = useState({});
//   const [suggestion, setSuggestion] = useState('');
//   const [joinedDatasets, setJoinedDatasets] = useState({});
//   const [selectedDataset, setSelectedDataset] = useState(null);
//   const [sortedDatasetsCriteria, setSortedDatasetsCriteria] = useState({})

//   // Drag and Drop handlers
//   const handleDrop = (e) => {
//     e.preventDefault();
//     const droppedFiles = Array.from(e.dataTransfer.files);
//     setFiles((prevFiles) => [...prevFiles, ...droppedFiles]);
//   };

//   const handleDragOver = (e) => {
//     e.preventDefault();
//   };

//   const handleFileChange = (e) => {
//     const selectedFiles = Array.from(e.target.files);
//     setFiles((prevFiles) => [...prevFiles, ...selectedFiles]);
//   };

//   const handleClick = () => {
//     fileInputRef.current.click();
//   };

//   const handleMultipleFileUpload = async () => {
//     const formData = new FormData();

//     if (files.length > 1) {
//       for (let i = 0; i < files.length; i++) {
//         formData.append("files[]", files[i]);
//       }
//     } else {
//       alert("Please upload at least two files");
//       return;
//     }

//     setLoading(true);

//     try {
//       const res = await axios.post(
//         "http://127.0.0.1:5000/process_multiple_datasets",
//         formData,
//         {
//           headers: {
//             "Content-Type": "multipart/form-data",
//           },
//         }
//       );

//       setMessage("Joinable datasets identified and suggestions generated successfully.");
//       let responseData = res.data;
//       if (typeof res.data === 'string') {
//         responseData = JSON.parse(res.data);
//       }

//       setSuggestion(responseData.suggestions);
//       setJoinedDatasets(responseData.joined_datasets);
//       setSortedDatasets(responseData.sorted_datasets);
//       setLevenshteinDistances(responseData.levenshtein_distances);
//       setSortedDatasetsCriteria(responseData.sorted_datasets_criteria);
//       // setDataset(responseData.datasets); // Assuming datasets are returned
//     } catch (err) {
//       console.error(err);
//       setMessage("File upload failed or invalid input.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   const handleDatasetClick = (selectedFile) => {
//     // Assuming each dataset is associated with its filename in the response
//     setSelectedDataset(selectedFile);
//     setDataset(joinedDatasets[selectedFile] || []); // Display dataset on the right
//   };

//   const columns = dataset && dataset.length > 0
//     ? Object.keys(dataset[0]).map((key) => ({
//         field: key,
//         headerName: key,
//         width: 150,
//       }))
//     : [];

//   const rows = dataset && dataset.map((row, index) => ({
//     id: index + 1,
//     ...row,
//   }));

//   return (
//     <div className="file-upload-container">
//       <div className="left-panel">
//         <h2>Uploaded Datasets</h2>
//         {files.length > 0 ? (
//           <ul>
//             {files.map((file, index) => (
//               <li key={index} onClick={() => handleDatasetClick(file.name)}>
//                 {file.name}
//               </li>
//             ))}
//           </ul>
//         ) : (
//           <p>No files uploaded yet</p>
//         )}
//       </div>

//       <div className="right-panel">
//         <h2>Upload Multiple Datasets</h2>
//         <div
//           className="drop-zone"
//           onDrop={handleDrop}
//           onDragOver={handleDragOver}
//           onClick={handleClick}
//         >
//           {files.length > 0 ? (
//             <p>{files.map(file => file.name).join(", ")}</p>
//           ) : (
//             <p>Drag & drop multiple files here, or click to select files</p>
//           )}
//           <input
//             type="file"
//             multiple
//             onChange={handleFileChange}
//             ref={fileInputRef}
//             style={{ display: "none" }}
//           />
//         </div>

//         <button onClick={handleMultipleFileUpload} disabled={files.length === 0} className="upload-btn">
//           Upload Files
//         </button>
        
//         <p>{message}</p>

//         {loading ? (
//           <div className="loader">
//             <RotatingLines
//               strokeColor="blue"
//               strokeWidth="3"
//               animationDuration="0.75"
//               width="70"
//               visible={true}
//             />
//           </div>
//         ) : (
//           <>
//             {suggestion && suggestion.map(item => <p key={item}>{item}</p>)}
//             {joinedDatasets && <JoinedDatasetDisplay joinedDatasets={joinedDatasets} />}
//             {sortedDatasets && <DatasetDisplay sortedDatasets={sortedDatasets} levenshteinDistances={levenshteinDistances} sortingCriterias={sortedDatasetsCriteria} />}
//             {dataset && dataset.length > 0 && (
//               <div className="table-div" style={{ height: 600, width: '80%' }}>
//                 <DataGrid rows={rows} columns={columns} pageSize={10} />
//               </div>
//             )}
//           </>
//         )}
//       </div>
//     </div>
//   );
// };

// export default FileUpload;




// after fall break, trying displaying datasets to the left

import React, { useRef, useState } from "react";
import axios from "axios";
import { RotatingLines, InfinitySpin } from "react-loader-spinner";
import DatasetDisplay from "./DatasetDisplay";

const FileUpload = () => {
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef(null);
  const [suggestion, setSuggestion] = useState([]);
  const [joinedDatasets, setJoinedDatasets] = useState({});
  const [sortedDatasets, setSortedDatasets] = useState({});
  const [levenshteinDistances, setLevenshteinDistances] = useState({});
  const [sortedDatasetsCriteria, setSortedDatasetsCriteria] = useState({});
  const [activeDatasetName, setActiveDatasetName] = useState(null);
  const [activeSortingColumns, setActiveSortingColumns] = useState([]);
  const [selectedColumn, setSelectedColumn] = useState(null); // Track the selected column
  const [showColumns, setShowColumns] = useState(false)

  // Handle multiple file uploads
  const handleMultipleFileUpload = async () => {
    const formData = new FormData();
    if (files.length > 1) {
      for (let i = 0; i < files.length; i++) {
        formData.append("files[]", files[i]);
      }
    } else {
      alert("Please upload at least two files");
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(
        "http://127.0.0.1:5000/process_multiple_datasets",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      const responseData = res.data;
      setMessage("Joinable datasets identified and suggestions generated successfully.");
      setSuggestion(responseData.suggestions);
      setJoinedDatasets(responseData.joined_datasets);
      setSortedDatasets(responseData.sorted_datasets);
      setSortedDatasetsCriteria(responseData.sorted_datasets_criteria);
      setLevenshteinDistances(responseData.levenshtein_distances);
    } catch (err) {
      console.error(err);
      setMessage("File upload failed or invalid input.");
    } finally {
      setLoading(false);
    }
  };

  // Handle dataset selection and display its columns
  const handleDatasetClick = (datasetName) => {
    if (datasetName === activeDatasetName) {
      setShowColumns(show => !show)
    }
    else{
    setActiveDatasetName(datasetName);
    const columns = Object.keys(sortedDatasets[datasetName]);
    setActiveSortingColumns(columns);
    setShowColumns(show => true)
    setSelectedColumn(null); // Reset the selected column
    }
  };

  // Handle column selection
  const handleColumnClick = (columnName) => {
    setSelectedColumn(columnName);
  };

  return (
    <div className="file-upload-container">
      <div className="left-panel">
        <h2>Joined Datasets</h2>
        {Object.keys(joinedDatasets).length > 0 ? (
          <ul>
            {Object.keys(joinedDatasets).map((datasetName, index) => (
              <li key={index}>
                <div onClick={() => handleDatasetClick(datasetName)} style={{ cursor: "pointer", wordWrap: "break-word" }} >
                  {datasetName}
                </div>
                {activeDatasetName === datasetName && activeSortingColumns.length > 0 && showColumns && (
                  <ul>
                    {activeSortingColumns.map((colName) => (
                      <li key={colName} onClick={() => handleColumnClick(colName)} style={{ cursor: "pointer", paddingLeft: "20px" }}>
                        {colName}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p>No joined datasets available</p>
        )}
      </div>

      <div className="right-panel">
        <h2 className="heading">Upload Multiple Datasets</h2>
        <div className="drop-zone" onClick={() => fileInputRef.current.click()}>
          {files.length > 0 ? (
            <p>{files.map((file) => file.name).join(", ")}</p>
          ) : (
            <p>Drag & drop multiple files here, or click to select files</p>
          )}
          <input type="file" multiple onChange={(e) => setFiles([...files, ...Array.from(e.target.files)])} ref={fileInputRef} style={{ display: "none" }} />
        </div>

        <button onClick={handleMultipleFileUpload} disabled={files.length === 0} className="upload-btn">
          Upload Files
        </button>

        <p className="message">{message}</p>

        {loading ? (
          // <RotatingLines strokeColor="blue" strokeWidth="3" animationDuration="0.75" width="70" visible={true} />
          <div className="loader">
          <InfinitySpin
  visible={true}
  width="200"
  color="#4fa94d"
  ariaLabel="infinity-spin-loading"
  />
  </div>
        ) : (
          <>
            {/* Display the DatasetDisplay when a column is selected */}
            {selectedColumn && activeDatasetName && (
              <DatasetDisplay
                activeDatasetName={activeDatasetName}
                sortingKey={selectedColumn}
                sortedDatasets={sortedDatasets}
                sortingCriterias={sortedDatasetsCriteria}
                levenshteinDistances={levenshteinDistances}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default FileUpload;
