import React, { useState } from "react";
import { DataGrid } from "@mui/x-data-grid";

const JoinedDatasetDisplay = ({ joinedDatasets }) => {
  // Check if there are joined datasets available
  if (!joinedDatasets || Object.keys(joinedDatasets).length === 0) {
    return <p>No joined datasets available.</p>;
  }

  const datasetKeys = Object.keys(joinedDatasets); // Get the list of joined datasets
  const [activeDatasetIndex, setActiveDatasetIndex] = useState(0); // Track the currently active dataset

  // Handler for moving to the next dataset
  const handleNext = () => {
    setActiveDatasetIndex((prevIndex) =>
      prevIndex === datasetKeys.length - 1 ? 0 : prevIndex + 1
    );
  };

  // Handler for moving to the previous dataset
  const handlePrev = () => {
    setActiveDatasetIndex((prevIndex) =>
      prevIndex === 0 ? datasetKeys.length - 1 : prevIndex - 1
    );
  };

  // Get the current dataset and its key (e.g., 'dataset_0_dataset_1_joined')
  const activeDatasetKey = datasetKeys[activeDatasetIndex];
  const activeDataset = joinedDatasets[activeDatasetKey];

  // Helper function to render datasets in DataGrid
  const renderDataset = (dataset) => {
    const columns =
      dataset.length > 0
        ? Object.keys(dataset[0]).map((key) => ({
            field: key,
            headerName: key,
            width: 150
          }))
        : [];

    const rows = dataset.map((row, index) => ({
      id: index + 1,
      ...row
    }));

    return (
      <div style={{ height: 400, width: "100%", marginBottom: "20px" }}>
        <DataGrid rows={rows} columns={columns} pageSize={5} />
      </div>
    );
  };

  return (
    <div>
      <h2>Joined Dataset: {activeDatasetKey}</h2>

      <div style={{ width: "70%", margin: "0 auto" }}>
        {/* Display the active dataset */}
        {renderDataset(activeDataset)}
      </div>

      {/* Scroll Buttons */}
      <div
        style={{
          marginTop: "20px",
          display: "flex",
          justifyContent: "center"
        }}
      >
        <button onClick={handlePrev} style={{ marginRight: "10px" }}>
          Previous
        </button>
        <button onClick={handleNext}>Next</button>
      </div>
    </div>
  );
};

export default JoinedDatasetDisplay;
