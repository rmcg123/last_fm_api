"""Main script for Last FM analysis."""
import pandas as pd
from matplotlib import rcParams

import src.last_fm_config as cfg
import src.last_fm_functions as lf

rcParams["font.family"] = "Arial"
rcParams["figure.figsize"] = (16, 9)
rcParams["figure.dpi"] = 300
rcParams["axes.titlesize"] = 24
rcParams["axes.labelsize"] = 18
rcParams["font.size"] = 16
rcParams["xtick.labelsize"] = 16
rcParams["ytick.labelsize"] = 14
rcParams["legend.fontsize"] = 12
rcParams["legend.title_fontsize"] = 16


def geographic_top_artists():
    """Retrieve the artists with most last.fm listeners for each country and
    create a map showing each countries top artist."""

    # Load top artists from each country.
    try:
        country_artists_df = pd.read_csv(
            cfg.DATA_PATH + "country_artists_df.csv"
        )
    except FileNotFoundError:
        country_artists_df = lf.get_countries_top_artists(
            countries=cfg.COUNTRIES,
            last_fm_api_url=cfg.LAST_FM_API_ROOT,
            request_headers={"user-agent": cfg.USER_AGENT},
            request_params={
                "format": "json",
                "method": "geo.gettopartists",
                "api_key": cfg.LAST_FM_API_KEY,
            },
            country_name_changes=cfg.COUNTRY_NAME_CHANGES,
        )
        country_artists_df.sort_values(
            by=["country", "country_rank"], inplace=True
        )
        country_artists_df.to_csv(
            cfg.DATA_PATH + "country_artists_df.csv", index=False
        )

    # Create a world map showing top artist for each country.
    _, _ = lf.create_top_artists_world_map(
        country_artists_df,
        country_name_mappings=cfg.COUNTRY_NAME_MAPPING,
        save_dir=cfg.RESULTS_PATH,
        save_name="top_artist_world_map.png",
    )

    # Create listener fraction world map.
    _, _ = lf.create_listener_fraction_world_map(
        country_artists_df,
        country_name_mappings=cfg.COUNTRY_NAME_MAPPING,
        save_dir=cfg.RESULTS_PATH,
        save_name="listener_frac_world_map.png",
    )


def overall_top_artists():
    """Look at overall listener and play statistics from last.fm."""

    # Retrieve the top 2000 artists on last.fm.
    try:
        top_artists_df = pd.read_csv(cfg.DATA_PATH + "top_artists_df.csv")
    except FileNotFoundError:
        top_artists_df = lf.get_top_artists(
            last_fm_api_url=cfg.LAST_FM_API_ROOT,
            request_headers={"user-agent": cfg.USER_AGENT},
            request_params={
                "method": "chart.gettopartists",
                "format": "json",
                "api_key": cfg.LAST_FM_API_KEY,
            },
            n_artists=2000,
            artists_per_page=50,
        )
        top_artists_df.drop_duplicates(subset=["mbid"], inplace=True)
        top_artists_df.to_csv(cfg.DATA_PATH + "top_artists_df.csv")

    # Format columns and create average plays per listener column.
    top_artists_df["playcount"] = top_artists_df["playcount"].astype(float)
    top_artists_df["listeners"] = top_artists_df["listeners"].astype(float)
    top_artists_df["plays_per_listener"] = (
        top_artists_df["playcount"] / top_artists_df["listeners"]
    )

    # Create basic summary plots.
    for stat in ["listeners", "playcount", "plays_per_listener"]:
        lf.plot_barplot(
            top_artists_df=top_artists_df,
            x_col=stat,
            y_col="name",
            save_dir=cfg.RESULTS_PATH,
            save_name=f"{stat}.png",
        )


def my_listening_history():
    """Function to retrieve my listening history and make some summary plots
    showing longitudinal listening trends and timing of listening."""

    # Retrieve my listening history.
    try:
        tracks_df = pd.read_csv(cfg.DATA_PATH + "tracks_df.csv")
    except FileNotFoundError:
        tracks_df = lf.get_all_listening_history(
            last_fm_api_url=cfg.LAST_FM_API_ROOT,
            request_headers={"user-agent": cfg.USER_AGENT},
            request_params={
                "api_key": cfg.LAST_FM_API_KEY,
                "format": "json",
                "method": "user.getrecenttracks",
            },
            user=cfg.LAST_FM_USERNAME,
            tracks_per_page=200,
        )
        tracks_df.to_csv(cfg.DATA_PATH + "tracks_df.csv")

    # Clean up columns.
    tracks_df["datetime"] = pd.to_datetime(
        tracks_df["date.#text"], format="%d %b %Y, %H:%M"
    )
    tracks_df.rename(
        columns={
            "artist.#text": "artist",
            "album.#text": "album",
        },
        inplace=True,
    )

    # Determine top 6 most listened artists. Create rolling listening count of
    # last 365 days for these 6 artists.
    top_6_artists = list(tracks_df["artist"].value_counts().head(6).index)
    rolling_listening = (
        tracks_df.loc[tracks_df["artist"].isin(top_6_artists)]
        .set_index("datetime")
        .groupby("artist")
        .rolling("365d", min_periods=1)["name"]
        .count()
        .reset_index()
    )

    # Plot rolling listening count.
    _, _ = lf.longitudinal_plot(
        rolling_listening,
        order=top_6_artists,
        save_dir=cfg.RESULTS_PATH,
        save_name="rolling_listening.png",
    )

    # Create hour and year columns.
    tracks_df["hour"] = tracks_df["datetime"].dt.hour
    tracks_df["year"] = tracks_df["datetime"].dt.year

    # Create count of plays by hour and year.
    hour_year_counts = pd.pivot_table(
        data=tracks_df,
        index="year",
        columns="hour",
        values="name",
        aggfunc="count",
    )

    # Focus only on complete listening years.
    hour_year_counts = hour_year_counts.loc[list(range(2015, 2023, 1)), :]

    # Calculate daily average.
    hour_year_counts = (
        hour_year_counts.T / ([365, 366, 365, 365, 365, 366, 365, 365])
    ).T

    # Produce heatmap showing information
    _, _ = lf.listening_timing_heatmap(
        listen_hour_counts=hour_year_counts,
        save_dir=cfg.RESULTS_PATH,
        save_name="year_hour_counts.png",
    )


def main():
    """Main function for analysis."""

    geographic_top_artists()

    overall_top_artists()

    my_listening_history()


if __name__ == "__main__":
    main()
