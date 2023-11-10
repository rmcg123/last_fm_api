"""Functions to help with the Last FM analysis."""
import time

import numpy as np
import pandas as pd
import requests
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns


def _send_last_fm_artist_request(
    last_fm_api_url, request_headers, request_params, outer_col="topartists"
):
    """Function to send a request to the last.fm api for artist based methods."""

    # Send request.
    req = requests.get(
        last_fm_api_url, headers=request_headers, params=request_params
    )

    # If the request was successful then parse the response, otherwise return
    # an empty DataFrame.
    if req.status_code == 200:
        artists_df = pd.json_normalize(req.json()[outer_col]["artist"])
    else:
        artists_df = pd.DataFrame()

    return artists_df


def get_countries_top_artists(
    countries,
    last_fm_api_url,
    request_headers,
    request_params,
    country_name_changes,
):
    """Function to loop through countries and send a request for the 50
    artists with the most listeners for that country."""

    # Loop through countries.
    country_artists_df = pd.DataFrame()
    for country in countries:
        # Last Fm uses outdated name for Czechia, otherwise ISO-3166 is adhered
        # to.
        if country in country_name_changes:
            country = country_name_changes[country]

        print(f"Getting top 50 artists for {country}...")
        request_params["country"] = country

        # Send request and get response.
        country_artist_df = _send_last_fm_artist_request(
            last_fm_api_url,
            request_headers=request_headers,
            request_params=request_params,
        )

        # If data was returned then add to accruing DataFrame.
        if len(country_artist_df) > 0:
            country_artist_df.drop(columns=["image"], inplace=True)
            country_artist_df["country_rank"] = country_artist_df.index + 1
            country_artist_df["country"] = country

            country_artists_df = pd.concat(
                [country_artists_df, country_artist_df], ignore_index=True
            )

        # Adhere to rate limiting.
        time.sleep(1)

    # Format column data type.
    country_artists_df["listeners"] = country_artists_df["listeners"].astype(
        float
    )

    return country_artists_df


def create_top_artists_world_map(
    country_artists_df, country_name_mappings, save_dir, save_name
):
    """Function to create a plot showing a world map with the artist with the
    most last.fm listeners for each country."""

    fig, ax = plt.subplots()

    # Load the natural earth low res map from geopandas. Rename country name
    # column to facilitate merge. Correct deviations from ISO-3166.
    world_map_path = gpd.datasets.get_path("naturalearth_lowres")
    world_map = gpd.read_file(world_map_path)
    world_map.rename(columns={"name": "country"}, inplace=True)
    world_map["country"] = (
        world_map["country"]
        .map(country_name_mappings)
        .fillna(world_map["country"])
    )

    # Select the top artist from each country.
    top_artists = country_artists_df.loc[
        country_artists_df["country_rank"].eq(1)
    ]

    # Only explicitly show artist that are highest in 2 or more countries.
    more_than_one_country = list(
        top_artists["name"]
        .value_counts()[top_artists["name"].value_counts().ge(2)]
        .index
    )

    # Otherwise create an "Other" category.
    top_artists.loc[
        ~top_artists["name"].isin(more_than_one_country), "name"
    ] = "Other"

    # Merge world map geometry with listeners.
    world_map = world_map.merge(
        top_artists[["country", "name", "listeners"]], how="left", on="country"
    )

    # Create plot.
    world_map.plot(
        column="name",
        edgecolor="black",
        legend=True,
        cmap="tab20b",
        missing_kwds={"color": "lightgrey", "label": "No Data"},
        ax=ax,
        legend_kwds={
            "title": "Artist",
            "loc": "upper center",
            "bbox_to_anchor": (0.5, 0),
            "ncols": 6,
        },
    )

    # Set title and appearance.
    ax.set_title("Artists with most last.fm listeners by country")
    ax.set_axis_off()

    # Save plot.
    fig.savefig(save_dir + save_name, bbox_inches="tight")

    return fig, ax


def create_listener_fraction_world_map(
    country_artists_df, country_name_mappings, save_dir, save_name
):
    """Function to create a plot showing a world map with the percentage of
    population listening to artist with the most last.fm listeners for each
    country."""

    fig, ax = plt.subplots()

    # Load the natural earth low res map from geopandas. Rename country name
    # column to facilitate merge. Correct deviations from ISO-3166.
    world_map_path = gpd.datasets.get_path("naturalearth_lowres")
    world_map = gpd.read_file(world_map_path)
    world_map.rename(columns={"name": "country"}, inplace=True)
    world_map["country"] = (
        world_map["country"]
        .map(country_name_mappings)
        .fillna(world_map["country"])
    )

    # Select the top artist from each country.
    top_artists = country_artists_df.loc[
        country_artists_df["country_rank"].eq(1)
    ]

    # Merge world map geometry with listeners.
    world_map = world_map.merge(
        top_artists[["country", "name", "listeners"]], how="left", on="country"
    )

    world_map["listener_percentage"] = np.where(
        world_map["listeners"].lt(world_map["pop_est"]),
        (100 * world_map["listeners"] / world_map["pop_est"]),
        np.nan,
    )

    # Create plot.
    world_map.plot(
        column="listener_percentage",
        edgecolor="black",
        legend=True,
        cmap="Greens",
        missing_kwds={"color": "lightgrey", "label": "No Data"},
        ax=ax,
        vmin=0,
        vmax=100,
        legend_kwds={
            "label": "% of population listening to top artist",
            "shrink": 0.6,
            "aspect": 15,
        },
    )

    # Set title and appearance.
    ax.set_title("Percentage of population listening to top artist by country")
    ax.set_axis_off()

    # Save plot.
    fig.savefig(save_dir + save_name, bbox_inches="tight")

    return fig, ax


def get_top_artists(
    last_fm_api_url,
    request_headers,
    request_params,
    n_artists,
    artists_per_page,
):
    """Function to retrieve the information for the top n artists."""

    # Determine number of requests required to reach n artists.
    n_requests = int(np.ceil(n_artists / artists_per_page))
    request_params["limit"] = artists_per_page

    # Loop over number of requests getting top artists.
    top_artists_df = pd.DataFrame()
    for page in range(1, n_requests + 1):
        request_params["page"] = page

        # Send request.
        top_artists = _send_last_fm_artist_request(
            last_fm_api_url=last_fm_api_url,
            request_headers=request_headers,
            request_params=request_params,
            outer_col="artists",
        )
        top_artists.drop(columns=["image"], inplace=True)
        top_artists["rank"] = (top_artists.index + 1) + 200 * (page - 1)

        # Add response to accruing DataFrame.
        top_artists_df = pd.concat(
            [top_artists_df, top_artists], ignore_index=True
        )

        # Handle rate limiting.
        time.sleep(1)

    return top_artists_df


def plot_barplot(top_artists_df, x_col, y_col, save_dir, save_name):
    """Plotting function to create some simple summary barplot of artist statistics."""

    fig, ax = plt.subplots()

    # Determine top 20 of chosen statistic.
    plot_data = top_artists_df.sort_values(by=[x_col], ascending=False).head(
        20
    )

    # Create barplot.
    sns.barplot(data=plot_data, x=x_col, y=y_col, orient="h")

    # Set titles and labels.
    ax.set_xlabel(x_col.replace("_", " ").title())
    ax.set_ylabel("Artist")
    ax.set_title(f"{x_col.replace('_', ' ').title()} by Artist")

    # Save plot.
    fig.savefig(save_dir + save_name, bbox_inches="tight")

    return fig, ax


def _get_listening_history(last_fm_api_url, request_headers, request_params):
    """Function to send a request to get (some of) my listening history."""

    # Send request.
    req = requests.get(
        last_fm_api_url, headers=request_headers, params=request_params
    )

    # If request successful then create DataFrame from response, otherwise return empty DataFrame.
    if req.status_code == 200:
        tracks_df = pd.json_normalize(req.json()["recenttracks"]["track"])
    else:
        tracks_df = pd.DataFrame()

    return tracks_df


def get_all_listening_history(
    last_fm_api_url, request_headers, request_params, user, tracks_per_page
):
    """Determine the number of pages required to retrieve my complete listening
    history then loop over each page sending request and receiving response."""

    # Set up request parameters.
    request_params["user"] = user
    request_params["limit"] = tracks_per_page

    # Use these to send a test request in order to determine the number of pages.
    tst = requests.get(
        last_fm_api_url, headers=request_headers, params=request_params
    )
    total_pages = int(tst.json()["recenttracks"]["@attr"]["totalPages"])

    # Loop over each page sending request and adding response to accruing
    # DataFrame.
    tracks_df = pd.DataFrame()
    for page in range(total_pages):
        print(f"Getting tracks for page {page}")
        request_params["page"] = page

        # Send request.
        tracks = _get_listening_history(
            last_fm_api_url=last_fm_api_url,
            request_headers=request_headers,
            request_params=request_params,
        )
        tracks.drop(columns=["image"], inplace=True)

        # Save tracks and add to DataFrame.
        tracks.to_csv(f"data/my_tracks/page_{page}.csv")
        tracks_df = pd.concat([tracks_df, tracks], ignore_index=True)

        # Handle rate limiting.
        time.sleep(2)

    return tracks_df


def longitudinal_plot(rolling_listening, order, save_dir, save_name):
    """Simple longitudinal plot to show listens for selected artists over the
    previous 365 days."""

    fig, ax = plt.subplots()

    # Create line plots.
    sns.lineplot(
        data=rolling_listening,
        x="datetime",
        y="name",
        hue="artist",
        hue_order=order,
    )

    # Set axes titles and labels.
    ax.set_title(
        "Rolling listens last 365 days over time for my top 6 listened artists"
    )
    ax.set_ylabel("Rolling listens last 365 days")
    ax.set_xlabel("Date")

    # Save figure.
    fig.savefig(save_dir + save_name, bbox_inches="tight")

    return fig, ax


def listening_timing_heatmap(listen_hour_counts, save_dir, save_name):
    """Create heatmap showing the average daily track plays by year and hour of
    day."""

    fig, ax = plt.subplots()

    # Create heatmap.
    sns.heatmap(
        data=listen_hour_counts,
        cmap="plasma",
        square=True,
        cbar_kws={
            "shrink": 0.5,
            "aspect": 12,
            "label": "Average daily track plays",
            "pad": 0.01,
        },
        linecolor="black",
        linewidths=0.25,
        ax=ax,
    )

    # Adjust yticklabels orientation.
    yticklabels = ax.get_yticklabels()
    ax.set_yticklabels(yticklabels, rotation=0)
    ax.set_title("Average Daily Track Plays by Year and Hour of Day")

    # Save figure.
    fig.savefig(save_dir + save_name, bbox_inches="tight")

    return fig, ax
